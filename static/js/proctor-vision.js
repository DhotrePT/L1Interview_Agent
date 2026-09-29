/* Camera and microphone proctoring.
 *
 * Watches the interview video feed and reports four things the DOM events in
 * app.js cannot see:
 *
 *   multiple_faces     a second person in frame
 *   no_face            the candidate has left the frame
 *   looking_away       sustained gaze or head turn away from the screen
 *   electronic_device  a phone, tablet, laptop or TV in frame
 *   second_voice       speech while the candidate's own mouth is shut
 *
 * Everything here is advisory. If the models fail to load - offline, CDN
 * blocked, unsupported browser, no WebGL - the watcher disables itself and the
 * interview continues with DOM-event proctoring only. A proctor that breaks the
 * exam is worse than one that misses a cheat.
 *
 * TUNING. Every detector demands *sustained* evidence before it costs the
 * candidate a strike, because termination is three strikes. A glance at the
 * keyboard, a flatmate crossing the room, a hand raised to the chin - none of
 * those should end an interview. The constants below are deliberately
 * conservative and want calibrating against real recordings before this is
 * used to reject anyone.
 */

const WASM_BASE =
  "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm";
const FACE_MODEL =
  "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task";
const OBJECT_MODEL =
  "https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite0/float16/1/efficientdet_lite0.tflite";

const CONFIG = {
  faceIntervalMs: 250, //  4 fps - enough for presence and gaze
  objectIntervalMs: 1000, //  1 fps - detection is the expensive one

  // How long a condition must hold continuously before it is reported.
  sustain: {
    multipleFacesMs: 2500,
    noFaceMs: 8000, //  generous: leaning out of frame is not cheating
    lookingAwayMs: 5000, //  long, on purpose - see TUNING above
    deviceMs: 2000,
    secondVoiceMs: 3000,
  },

  // Minimum gap between two reports of the same type, so one continuous
  // violation costs one strike rather than emptying the candidate's budget.
  cooldownMs: 30000,

  // Head rotation, radians, beyond which the candidate is "not facing forward".
  // ~0.5 rad is about 29 degrees.
  yawLimit: 0.5,
  pitchLimit: 0.45,

  deviceConfidence: 0.45,
  deviceLabels: new Set([
    "cell phone",
    "laptop",
    "tv",
    "remote",
    "keyboard",
    "mouse",
    "book",
  ]),

  // Microphone level above which someone is speaking, and the jawOpen
  // blendshape below which the candidate's own mouth is shut.
  voiceRms: 0.045,
  mouthShutBelow: 0.12,
};

/* A condition that must hold continuously before it fires, then goes quiet for
 * a cooldown. Returns true exactly once per sustained episode. */
function sustained(holdMs) {
  return {
    since: 0,
    lastFired: 0,
    update(active, now) {
      if (!active) {
        this.since = 0;
        return false;
      }
      if (!this.since) this.since = now;
      if (now - this.since < holdMs) return false;
      if (now - this.lastFired < CONFIG.cooldownMs) return false;
      this.lastFired = now;
      this.since = now;
      return true;
    },
  };
}

/* Yaw and pitch from MediaPipe's facial transformation matrix. The matrix
 * arrives as 16 floats in column-major order, so element (row, col) is
 * data[col * 4 + row]. */
function headAngles(matrixData) {
  const at = (row, col) => matrixData[col * 4 + row];
  const r02 = at(0, 2);
  const r12 = at(1, 2);
  const r22 = at(2, 2);
  const yaw = Math.asin(Math.max(-1, Math.min(1, r02)));
  const pitch = Math.atan2(-r12, r22);
  return { yaw, pitch };
}

const proctorVision = {
  running: false,
  available: false,
  reason: "",
  faceLandmarker: null,
  objectDetector: null,
  timers: [],
  audio: null,
  onFlag: null,
  video: null,
  lastJawOpen: 0,

  state: {
    multipleFaces: sustained(CONFIG.sustain.multipleFacesMs),
    noFace: sustained(CONFIG.sustain.noFaceMs),
    lookingAway: sustained(CONFIG.sustain.lookingAwayMs),
    device: sustained(CONFIG.sustain.deviceMs),
    secondVoice: sustained(CONFIG.sustain.secondVoiceMs),
  },

  async start({ video, stream, onFlag }) {
    if (this.running) return this.available;
    this.video = video;
    this.onFlag = onFlag;

    try {
      const vision = await import(
        "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/vision_bundle.mjs"
      );
      const files = await vision.FilesetResolver.forVisionTasks(WASM_BASE);

      this.faceLandmarker = await vision.FaceLandmarker.createFromOptions(files, {
        baseOptions: { modelAssetPath: FACE_MODEL, delegate: "GPU" },
        runningMode: "VIDEO",
        numFaces: 3, // we only need to know "more than one"
        outputFaceBlendshapes: true,
        outputFacialTransformationMatrixes: true,
      });

      this.objectDetector = await vision.ObjectDetector.createFromOptions(files, {
        baseOptions: { modelAssetPath: OBJECT_MODEL, delegate: "GPU" },
        runningMode: "VIDEO",
        scoreThreshold: CONFIG.deviceConfidence,
      });
    } catch (err) {
      this.available = false;
      this.reason = String((err && err.message) || err);
      console.warn("Camera proctoring unavailable, continuing without it:", err);
      return false;
    }

    this.startAudio(stream);
    this.running = true;
    this.available = true;
    this.timers.push(setInterval(() => this.tickFace(), CONFIG.faceIntervalMs));
    this.timers.push(setInterval(() => this.tickObjects(), CONFIG.objectIntervalMs));
    return true;
  },

  startAudio(stream) {
    try {
      const track = stream && stream.getAudioTracks()[0];
      if (!track) return;
      const Ctx = window.AudioContext || window.webkitAudioContext;
      const ctx = new Ctx();
      const source = ctx.createMediaStreamSource(new MediaStream([track]));
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 1024;
      source.connect(analyser);
      this.audio = { ctx, analyser, buffer: new Float32Array(analyser.fftSize) };
    } catch (err) {
      console.warn("Voice watch unavailable:", err);
    }
  },

  micLevel() {
    if (!this.audio) return 0;
    this.audio.analyser.getFloatTimeDomainData(this.audio.buffer);
    let sum = 0;
    for (const v of this.audio.buffer) sum += v * v;
    return Math.sqrt(sum / this.audio.buffer.length);
  },

  ready() {
    const v = this.video;
    return this.running && v && v.readyState >= 2 && v.videoWidth > 0;
  },

  fire(type, detail) {
    if (this.onFlag) this.onFlag(type, detail);
  },

  tickFace() {
    if (!this.ready()) return;
    let result;
    try {
      result = this.faceLandmarker.detectForVideo(this.video, performance.now());
    } catch {
      return; // a dropped frame is not worth a strike
    }

    const now = Date.now();
    const faces = (result.faceLandmarks || []).length;

    if (this.state.multipleFaces.update(faces > 1, now)) {
      this.fire("multiple_faces", `${faces} faces detected in frame`);
    }
    if (this.state.noFace.update(faces === 0, now)) {
      this.fire("no_face", "No face visible on camera");
    }

    if (faces !== 1) return; // gaze and mouth only mean something for one face

    const matrices = result.facialTransformationMatrixes || [];
    if (matrices.length) {
      const { yaw, pitch } = headAngles(matrices[0].data);
      const away =
        Math.abs(yaw) > CONFIG.yawLimit || Math.abs(pitch) > CONFIG.pitchLimit;
      if (this.state.lookingAway.update(away, now)) {
        const deg = (r) => Math.round((r * 180) / Math.PI);
        this.fire("looking_away", `Head turned yaw ${deg(yaw)} deg, pitch ${deg(pitch)} deg`);
      }
    }

    const shapes = (result.faceBlendshapes || [])[0];
    if (shapes) {
      const jaw = shapes.categories.find((c) => c.categoryName === "jawOpen");
      this.lastJawOpen = jaw ? jaw.score : 0;
    }

    // Someone is speaking and it is not the candidate: audio is live while the
    // candidate's own mouth is shut.
    const speaking = this.micLevel() > CONFIG.voiceRms;
    const mouthShut = this.lastJawOpen < CONFIG.mouthShutBelow;
    if (this.state.secondVoice.update(speaking && mouthShut, now)) {
      this.fire("second_voice", "Voice detected while the candidate was not speaking");
    }
  },

  tickObjects() {
    if (!this.ready()) return;
    let result;
    try {
      result = this.objectDetector.detectForVideo(this.video, performance.now());
    } catch {
      return;
    }

    const hits = (result.detections || [])
      .map((d) => (d.categories && d.categories[0]) || null)
      .filter((c) => c && CONFIG.deviceLabels.has(c.categoryName) && c.score >= CONFIG.deviceConfidence);

    const seen = hits.length > 0;
    if (this.state.device.update(seen, Date.now())) {
      const what = hits
        .map((c) => `${c.categoryName} ${(c.score * 100).toFixed(0)}%`)
        .join(", ");
      this.fire("electronic_device", `Visible on camera: ${what}`);
    }
  },

  stop() {
    this.running = false;
    for (const t of this.timers) clearInterval(t);
    this.timers = [];
    if (this.audio) {
      try {
        this.audio.ctx.close();
      } catch {
        /* already closed */
      }
      this.audio = null;
    }
  },
};

window.proctorVision = proctorVision;
