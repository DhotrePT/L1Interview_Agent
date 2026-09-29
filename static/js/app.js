/* L1 Interview Agent - front end.
   Stages: login -> dashboard -> device check -> job description -> interview -> scorecard. */

const $ = (id) => document.getElementById(id);

const state = {
  sessionId: null,
  email: null,
  fullName: "",
  jobTitle: "",
  config: { proctor_alarm_at: 3, proctor_terminate_at: 6 },
  stream: null,
  recorder: null,
  audioCtx: null,
  analyser: null,
  levelTimer: null,
  questions: [],
  answers: {},
  index: 0,
  deadline: null,
  timerTick: null,
  startedAt: null,
  editor: null,
  recognition: null,
  listening: false,
  questionEnteredAt: null,
  finished: false,
};

/* ------------------------------------------------------------------ helpers */

async function api(path, { method = "GET", body = null, raw = null } = {}) {
  const options = { method, headers: {} };
  if (raw) {
    options.body = raw;
    options.headers["Content-Type"] = "application/octet-stream";
  } else if (body) {
    options.body = JSON.stringify(body);
    options.headers["Content-Type"] = "application/json";
  }
  const response = await fetch(path, options);
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
  return data;
}

function showStage(id) {
  document.querySelectorAll(".stage").forEach((s) => s.classList.remove("active"));
  $(id).classList.add("active");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

function formatDate(iso) {
  if (!iso) return "-";
  return new Date(iso).toLocaleString(undefined, {
    day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

fetch("/api/config")
  .then((r) => r.json())
  .then((cfg) => {
    state.config = cfg;
    $("rule-alarm").textContent = cfg.proctor_alarm_at;
    $("rule-terminate").textContent = cfg.proctor_terminate_at;
  })
  .catch(() => {});

/* ------------------------------------------------------------- stage: login */

$("login-btn").addEventListener("click", async () => {
  const email = $("email").value.trim();
  const error = $("login-error");
  error.classList.add("hidden");

  if (!email) {
    error.textContent = "Please enter your email address.";
    error.classList.remove("hidden");
    return;
  }

  $("login-btn").disabled = true;
  try {
    const data = await api("/api/auth/login", { method: "POST", body: { email } });
    state.email = data.email;
    state.fullName = $("full-name").value.trim();
    renderDashboard(data);
    showStage("stage-dashboard");
  } catch (err) {
    error.textContent = err.message;
    error.classList.remove("hidden");
  } finally {
    $("login-btn").disabled = false;
  }
});

$("email").addEventListener("keydown", (e) => {
  if (e.key === "Enter") $("login-btn").click();
});

/* --------------------------------------------------------- stage: dashboard */

async function refreshDashboard() {
  const data = await api(`/api/dashboard?email=${encodeURIComponent(state.email)}`);
  renderDashboard(data);
  showStage("stage-dashboard");
}

function statusPill(row) {
  if (row.status === "terminated") return '<span class="pill bad">Terminated</span>';
  if (row.status === "submitted") return '<span class="pill good">Completed</span>';
  if (row.status === "abandoned") return '<span class="pill mid">Not finished</span>';
  return '<span class="pill mid">In progress</span>';
}

function renderDashboard(data) {
  $("dash-email").textContent = state.fullName
    ? `${state.fullName} (${data.email})`
    : data.email;

  const attempts = data.attempts || [];
  $("attempts-body").innerHTML = attempts.length
    ? `<table class="breakdown">
         <thead><tr>
           <th>Post</th><th>Taken on</th><th>Status</th>
           <th class="num">Score</th><th>Outcome</th><th></th>
         </tr></thead>
         <tbody>${attempts.map((row) => `
           <tr>
             <td><strong>${escapeHtml(row.job_title || row.job_id || "-")}</strong></td>
             <td class="muted small">${escapeHtml(formatDate(row.started_at))}</td>
             <td>${statusPill(row)}${row.flagged
                 ? ` <span class="pill bad">&#9888; ${row.violations}</span>`
                 : ""}</td>
             <td class="num">${row.total_score === null || row.total_score === undefined
                 ? "-" : `<strong>${row.total_score}</strong> / 100`}</td>
             <td class="small">${escapeHtml(row.recommendation || "-")}
               <div class="muted small">${escapeHtml(row.grade || "")}</div></td>
             <td class="num">${row.total_score !== null && row.total_score !== undefined
                 ? `<button class="linkish" data-scorecard="${escapeHtml(row.session_id)}">View scorecard</button>`
                 : ""}</td>
           </tr>`).join("")}
         </tbody>
       </table>`
    : `<p class="muted">You have not taken any interview yet. Pick a post below to start.</p>`;

  $("attempts-body").querySelectorAll("[data-scorecard]").forEach((button) => {
    button.addEventListener("click", () => viewPastScorecard(button.dataset.scorecard));
  });

  $("posts-body").innerHTML = (data.posts || []).map((post) => `
    <div class="post-card${post.can_apply ? "" : " done"}">
      <div class="post-head">
        <h3>${escapeHtml(post.title)}</h3>
        <span class="muted small">${escapeHtml(post.openings)} opening(s)</span>
      </div>
      <div class="muted small">${escapeHtml(post.company)} &middot; ${escapeHtml(post.location)}
        &middot; ${escapeHtml(post.experience)}</div>
      <p class="small">${escapeHtml(post.summary)}</p>
      <div class="tags">${post.tags.map((t) => `<span>${escapeHtml(t)}</span>`).join("")}</div>
      ${post.can_apply
        ? `<button class="primary" data-apply="${escapeHtml(post.id)}">Start L1 interview</button>`
        : `<div class="done-note">&#10003; Already completed${
            post.last_attempt && post.last_attempt.total_score !== null &&
            post.last_attempt.total_score !== undefined
              ? ` &middot; scored ${post.last_attempt.total_score}/100` : ""}</div>`}
    </div>`).join("");

  $("posts-body").querySelectorAll("[data-apply]").forEach((button) => {
    button.addEventListener("click", () => startApplication(button.dataset.apply, button));
  });
}

async function startApplication(jobId, button) {
  button.disabled = true;
  button.textContent = "Preparing...";
  try {
    const data = await api("/api/session/start", {
      method: "POST",
      body: { email: state.email, job_id: jobId, full_name: state.fullName },
    });
    state.sessionId = data.session_id;
    state.jobTitle = data.job_title;
    state.finished = false;
    $("device-job-line").textContent = `Interviewing for: ${data.job_title}`;
    resetDeviceStage();
    showStage("stage-devices");
  } catch (err) {
    alert(err.message);
  } finally {
    button.disabled = false;
    button.textContent = "Start L1 interview";
  }
}

$("logout-btn").addEventListener("click", exitToLogin);
$("back-to-dash-1").addEventListener("click", () => {
  stopRecording();
  refreshDashboard();
});
$("back-to-dash-2").addEventListener("click", refreshDashboard);
$("exit-btn").addEventListener("click", exitToLogin);

function exitToLogin() {
  stopRecording();
  proctor.stop();
  state.sessionId = null;
  state.questions = [];
  state.answers = {};
  state.email = null;
  $("email").value = "";
  $("full-name").value = "";
  $("scorecard").innerHTML = "";
  $("result-actions").classList.add("hidden");
  $("camera-dock").classList.add("hidden");
  showStage("stage-login");
}

async function viewPastScorecard(sessionId) {
  try {
    const data = await api(`/api/session/${sessionId}/scorecard`);
    state.sessionId = sessionId;
    $("scoring-spinner").classList.add("hidden");
    renderScorecard(
      data.scorecard,
      data.status === "terminated" ? "proctoring_terminated" : "submitted"
    );
    showStage("stage-result");
  } catch (err) {
    alert(err.message);
  }
}

/* ------------------------------------------------------ stage: device check */

function resetDeviceStage() {
  $("device-btn").classList.remove("hidden");
  $("device-btn").disabled = false;
  $("device-btn").textContent = "Enable camera & microphone";
  $("device-next").classList.add("hidden");
  $("device-error").classList.add("hidden");
}

function setRow(rowId, ok, detail) {
  const row = $(rowId);
  row.classList.toggle("ok", ok);
  row.classList.toggle("bad", !ok);
  $(rowId === "row-camera" ? "camera-detail" : "mic-detail").textContent = detail;
}

function startLevelMeter(stream) {
  try {
    state.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const source = state.audioCtx.createMediaStreamSource(stream);
    state.analyser = state.audioCtx.createAnalyser();
    state.analyser.fftSize = 512;
    source.connect(state.analyser);

    const buffer = new Uint8Array(state.analyser.frequencyBinCount);
    state.levelTimer = setInterval(() => {
      state.analyser.getByteTimeDomainData(buffer);
      let peak = 0;
      for (const sample of buffer) peak = Math.max(peak, Math.abs(sample - 128));
      const pct = Math.min(100, Math.round((peak / 90) * 100));
      const fill = $("level-fill");
      const dockMeter = document.querySelector("#mic-meter i");
      if (fill) fill.style.width = pct + "%";
      if (dockMeter) dockMeter.style.width = pct + "%";
    }, 100);
  } catch (err) {
    console.warn("Level meter unavailable", err);
  }
}

$("device-btn").addEventListener("click", async () => {
  const error = $("device-error");
  error.classList.add("hidden");
  $("device-btn").disabled = true;
  $("device-btn").textContent = "Requesting access...";

  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: { echoCancellation: true, noiseSuppression: true },
    });
    state.stream = stream;

    const videoTrack = stream.getVideoTracks()[0];
    const audioTrack = stream.getAudioTracks()[0];
    const cameraOk = Boolean(videoTrack && videoTrack.readyState === "live");
    const micOk = Boolean(audioTrack && audioTrack.readyState === "live");

    $("preview-video").srcObject = stream;
    $("preview-placeholder").classList.add("hidden");
    setRow("row-camera", cameraOk, cameraOk ? `Connected - ${videoTrack.label}` : "Not detected");
    setRow("row-mic", micOk, micOk ? `Connected - ${audioTrack.label}` : "Not detected");
    if (micOk) startLevelMeter(stream);

    const result = await api(`/api/session/${state.sessionId}/device-check`, {
      method: "POST",
      body: {
        camera: cameraOk,
        microphone: micOk,
        camera_label: videoTrack ? videoTrack.label : "",
        microphone_label: audioTrack ? audioTrack.label : "",
      },
    });

    if (result.passed) {
      $("device-btn").classList.add("hidden");
      $("device-next").classList.remove("hidden");
    } else {
      error.textContent = `Not ready: ${result.missing.join(" and ")} unavailable. Fix it and try again.`;
      error.classList.remove("hidden");
      $("device-btn").disabled = false;
      $("device-btn").textContent = "Retry";
    }
  } catch (err) {
    setRow("row-camera", false, "Blocked or unavailable");
    setRow("row-mic", false, "Blocked or unavailable");
    error.textContent =
      "Camera/microphone access was denied or no device was found. Allow access in your " +
      "browser (padlock icon in the address bar) and click Retry. " + err.message;
    error.classList.remove("hidden");
    $("device-btn").disabled = false;
    $("device-btn").textContent = "Retry";
  }
});

$("device-next").addEventListener("click", async () => {
  const { job_description: jd } = await api(`/api/session/${state.sessionId}/jd`);
  renderJd(jd);
  showStage("stage-jd");
});

/* ------------------------------------------------------- stage: description */

function renderJd(jd) {
  const list = (items) => `<ul>${(items || []).map((i) => `<li>${escapeHtml(i)}</li>`).join("")}</ul>`;
  $("jd-body").innerHTML = `
    <div class="jd-title">${escapeHtml(jd.title)}</div>
    <div class="jd-meta">${escapeHtml(jd.company)} &middot; ${escapeHtml(jd.location)} &middot;
      Experience: ${escapeHtml(jd.experience)} &middot; ${escapeHtml(jd.openings)} opening(s)</div>
    <p class="jd-summary">${escapeHtml(jd.summary)}</p>
    <h3>What you will do</h3>${list(jd.responsibilities)}
    <h3>Must have</h3>${list(jd.must_have)}
    <h3>Good to have</h3>${list(jd.good_to_have)}
    <h3>This interview</h3>${list(jd.interview_format)}
  `;
  $("jd-check").checked = false;
  $("jd-btn").disabled = true;
}

$("jd-check").addEventListener("change", (e) => {
  $("jd-btn").disabled = !e.target.checked;
});

$("jd-btn").addEventListener("click", async () => {
  $("jd-btn").disabled = true;
  try {
    await api(`/api/session/${state.sessionId}/confirm-jd`, { method: "POST" });
    const data = await api(`/api/session/${state.sessionId}/begin`, { method: "POST" });
    state.questions = data.questions;
    state.answers = data.answers || {};
    await enterFullscreen();           // must happen inside this click gesture
    startInterview(data.remaining_seconds, data.proctor);
  } catch (err) {
    alert(err.message);
    $("jd-btn").disabled = false;
  }
});

/* --------------------------------------------------------------- proctoring */

async function enterFullscreen() {
  try {
    if (!document.fullscreenElement) await document.documentElement.requestFullscreen();
  } catch (err) {
    console.warn("Fullscreen refused", err);
  }
}

const proctor = {
  enabled: false,
  count: 0,
  lastAt: {},
  lastGlobal: 0,
  fullscreenChangedAt: 0,
  handlers: [],

  start(initialCount) {
    this.enabled = true;
    this.count = initialCount || 0;
    this.updateChip();

    const on = (target, event, handler, options) => {
      target.addEventListener(event, handler, options);
      this.handlers.push([target, event, handler, options]);
    };

    on(document, "visibilitychange", () => {
      if (document.hidden) this.flag("tab_hidden", "Tab or window was hidden");
    });
    on(window, "blur", () => this.flag("window_blur", "Focus left the interview window"));

    on(document, "fullscreenchange", () => {
      this.fullscreenChangedAt = Date.now();
      if (!document.fullscreenElement && this.enabled) {
        this.flag("fullscreen_exit", "Fullscreen was exited");
        $("fullscreen-gate").classList.remove("hidden");
      } else {
        $("fullscreen-gate").classList.add("hidden");
      }
    });

    on(document, "contextmenu", (e) => {
      e.preventDefault();
      this.flag("context_menu", "Right-click menu");
    });

    for (const [event, type, label] of [
      ["copy", "copy_attempt", "Copy"],
      ["cut", "copy_attempt", "Cut"],
      ["paste", "paste_attempt", "Paste"],
    ]) {
      on(document, event, (e) => {
        e.preventDefault();
        this.flag(type, `${label} blocked`);
      }, true);
    }

    on(document, "keydown", (e) => {
      const key = (e.key || "").toLowerCase();
      const devtools =
        e.key === "F12" ||
        (e.ctrlKey && e.shiftKey && ["i", "j", "c"].includes(key)) ||
        (e.ctrlKey && ["u", "p", "s"].includes(key));
      const newWindow = (e.ctrlKey || e.metaKey) && ["t", "n", "w"].includes(key);
      if (devtools || newWindow) {
        e.preventDefault();
        this.flag(
          "devtools_key",
          `Blocked shortcut: ${e.ctrlKey ? "Ctrl+" : ""}${e.shiftKey ? "Shift+" : ""}${e.key}`
        );
      }
    }, true);

    on(window, "resize", () => {
      // Entering/leaving fullscreen resizes the window too - don't double count.
      if (Date.now() - this.fullscreenChangedAt < 1500) return;
      this.flag("window_resized", `Window is now ${window.outerWidth}x${window.outerHeight}`);
    });

    if (state.stream) {
      for (const track of state.stream.getTracks()) {
        const type = track.kind === "video" ? "camera_stopped" : "microphone_stopped";
        track.addEventListener("ended", () => this.flag(type, `${track.kind} track ended`));
        track.addEventListener("mute", () => this.flag(type, `${track.kind} track muted`));
      }
    }

    if (window.screen && window.screen.isExtended) {
      this.flag("multiple_displays", "An extended or second display is connected");
    }

    this.startCameraWatch();
  },

  // Watches the camera for a second person, a device in frame, a sustained look
  // away, or a voice that is not the candidate's. Best effort: if the models
  // cannot load the interview carries on with DOM-event proctoring alone.
  startCameraWatch() {
    if (!window.proctorVision || !state.stream) return;
    window.proctorVision
      .start({
        video: $("dock-video"),
        stream: state.stream,
        onFlag: (type, detail) => this.flag(type, detail),
      })
      .then((ok) => {
        if (!ok) console.warn("Camera proctoring off:", window.proctorVision.reason);
      })
      .catch((err) => console.warn("Camera proctoring failed to start", err));
  },

  stop() {
    this.enabled = false;
    for (const [target, event, handler, options] of this.handlers) {
      target.removeEventListener(event, handler, options);
    }
    this.handlers = [];
    if (window.proctorVision) window.proctorVision.stop();
    $("fullscreen-gate").classList.add("hidden");
    $("alarm").classList.add("hidden");
  },

  async flag(type, detail) {
    if (!this.enabled || state.finished) return;

    // Blur and visibilitychange fire together for one switch - count it once.
    const now = Date.now();
    if (now - (this.lastAt[type] || 0) < 2000) return;
    if (now - this.lastGlobal < 700) return;
    this.lastAt[type] = now;
    this.lastGlobal = now;

    try {
      const result = await api(`/api/session/${state.sessionId}/violation`, {
        method: "POST",
        body: {
          type,
          detail,
          at_second: Math.round((now - (state.startedAt || now)) / 1000),
        },
      });
      this.count = result.count;
      this.updateChip();

      if (result.terminate) {
        this.stop();
        await finishInterview("proctoring_terminated");
      } else if (result.alarm) {
        this.raiseAlarm(result.label, result.remaining_before_termination);
      }
    } catch (err) {
      console.warn("Violation report failed", err);
    }
  },

  updateChip() {
    const chip = $("violation-chip");
    if (!chip) return;
    chip.textContent = `${this.count} flag${this.count === 1 ? "" : "s"}`;
    chip.classList.toggle("warn", this.count > 0 && this.count < state.config.proctor_alarm_at);
    chip.classList.toggle("bad", this.count >= state.config.proctor_alarm_at);
  },

  raiseAlarm(reason, remaining) {
    $("alarm-reason").textContent = reason;
    $("alarm-count").textContent =
      `${this.count} flags recorded. ${remaining} more will end this interview automatically.`;
    $("alarm").classList.remove("hidden");
    beep();
  },
};

function beep() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "square";
    osc.frequency.value = 880;
    gain.gain.value = 0.08;
    osc.connect(gain).connect(ctx.destination);
    osc.start();
    osc.frequency.setValueAtTime(660, ctx.currentTime + 0.18);
    osc.stop(ctx.currentTime + 0.36);
    setTimeout(() => ctx.close().catch(() => {}), 600);
  } catch (err) {
    /* audio is a nicety, never a blocker */
  }
}

$("alarm-ack").addEventListener("click", async () => {
  $("alarm").classList.add("hidden");
  await enterFullscreen();
});

$("resume-fullscreen").addEventListener("click", async () => {
  await enterFullscreen();
  $("fullscreen-gate").classList.add("hidden");
});

/* ---------------------------------------------------------- stage: interview */

function startInterview(remainingSeconds, proctorInfo) {
  $("dock-video").srcObject = state.stream;
  $("camera-dock").classList.remove("hidden");
  startRecording();

  state.startedAt = Date.now();
  state.deadline = Date.now() + remainingSeconds * 1000;
  state.timerTick = setInterval(updateTimer, 500);
  updateTimer();

  buildProgressDots();
  showQuestion(0);
  showStage("stage-interview");
  proctor.start(proctorInfo ? proctorInfo.violations : 0);

  window.addEventListener("beforeunload", beforeUnload);
}

function beforeUnload(e) {
  if (!state.finished) {
    e.preventDefault();
    e.returnValue = "";
  }
}

function startRecording() {
  const candidates = [
    "video/webm;codecs=vp9,opus",
    "video/webm;codecs=vp8,opus",
    "video/webm",
  ];
  const mimeType = candidates.find((t) => window.MediaRecorder && MediaRecorder.isTypeSupported(t));
  if (!mimeType) {
    $("rec-label").textContent = "NO REC";
    $("rec-dot").style.background = "#8f9bb3";
    return;
  }

  state.recorder = new MediaRecorder(state.stream, { mimeType, videoBitsPerSecond: 1_000_000 });
  state.recorder.ondataavailable = async (event) => {
    if (!event.data || event.data.size === 0) return;
    try {
      const buffer = await event.data.arrayBuffer();
      await api(`/api/session/${state.sessionId}/recording-chunk`, { method: "POST", raw: buffer });
    } catch (err) {
      console.warn("Chunk upload failed", err);
    }
  };
  state.recorder.start(5000); // flush every 5s so nothing is lost on a crash
}

function stopRecording() {
  if (state.recorder && state.recorder.state !== "inactive") state.recorder.stop();
  if (state.levelTimer) clearInterval(state.levelTimer);
  if (state.stream) state.stream.getTracks().forEach((t) => t.stop());
  state.recorder = null;
  state.stream = null;
  $("rec-label").textContent = "ENDED";
  $("rec-dot").style.animation = "none";
}

function updateTimer() {
  const secondsLeft = Math.max(0, Math.floor((state.deadline - Date.now()) / 1000));
  const minutes = String(Math.floor(secondsLeft / 60)).padStart(2, "0");
  const seconds = String(secondsLeft % 60).padStart(2, "0");

  const timer = $("timer");
  timer.textContent = `${minutes}:${seconds}`;
  timer.classList.toggle("warn", secondsLeft <= 300 && secondsLeft > 60);
  timer.classList.toggle("danger", secondsLeft <= 60);

  if (secondsLeft === 0 && !state.finished) {
    clearInterval(state.timerTick);
    finishInterview("time_expired");
  }
}

function buildProgressDots() {
  $("progress-dots").innerHTML = state.questions.map(() => "<span></span>").join("");
}

function refreshProgressDots() {
  const dots = $("progress-dots").children;
  state.questions.forEach((question, i) => {
    const answer = state.answers[question.id] || {};
    const answered = (answer.answer || answer.code || "").trim().length > 0;
    dots[i].className = i === state.index ? "current" : answered ? "done" : "";
  });
}

function ensureEditor() {
  if (state.editor || typeof CodeMirror === "undefined") return;
  state.editor = CodeMirror.fromTextArea($("code-area"), {
    mode: "python",
    theme: "material-darker",
    lineNumbers: true,
    indentUnit: 4,
    tabSize: 4,
    indentWithTabs: false,
    lineWrapping: true,
    extraKeys: { Tab: (cm) => cm.replaceSelection("    ") },
  });
}

function getCode() {
  return state.editor ? state.editor.getValue() : $("code-area").value;
}

function setCode(value) {
  if (state.editor) {
    state.editor.setValue(value);
    setTimeout(() => state.editor.refresh(), 10);
  } else {
    $("code-area").value = value;
  }
}

function collectCurrentAnswer() {
  const question = state.questions[state.index];
  if (!question) return null;
  const previous = state.answers[question.id] || {};
  const spent = (previous.seconds_spent || 0) +
    Math.round((Date.now() - (state.questionEnteredAt || Date.now())) / 1000);

  return {
    question_id: question.id,
    answer: $("answer-text").value,
    code: question.type === "coding" ? getCode() : "",
    code_output: previous.code_output || "",
    explanation: $("explain-text").value,
    seconds_spent: spent,
  };
}

async function saveCurrentAnswer() {
  const payload = collectCurrentAnswer();
  if (!payload) return;
  state.answers[payload.question_id] = {
    answer: payload.answer,
    code: payload.code,
    code_output: payload.code_output,
    explanation: payload.explanation,
    seconds_spent: payload.seconds_spent,
  };
  // Reset the stopwatch so repeated saves on one question don't double-count the time.
  state.questionEnteredAt = Date.now();
  try {
    await api(`/api/session/${state.sessionId}/answer`, { method: "POST", body: payload });
    $("save-state").textContent = "Saved";
    setTimeout(() => ($("save-state").textContent = ""), 1500);
  } catch (err) {
    $("save-state").textContent = "Save failed - retrying on next step";
    console.warn(err);
  }
}

function showQuestion(index) {
  stopListening();
  state.index = index;
  state.questionEnteredAt = Date.now();

  const question = state.questions[index];
  const saved = state.answers[question.id] || {};
  const isCoding = question.type === "coding";

  $("q-type").textContent = question.type.toUpperCase();
  $("q-type").className = "badge " + question.type;
  $("q-title").textContent = `Q${question.number}. ${question.title}`;
  $("q-meta").textContent =
    `${question.weight} marks · suggested ${question.suggested_minutes} min · ` +
    `question ${question.number} of ${state.questions.length}`;
  $("q-prompt").textContent = question.prompt;

  $("answer-label").textContent = isCoding
    ? "Notes (optional - approach, complexity, assumptions)"
    : "Your answer";
  $("answer-text").value = saved.answer || "";
  $("answer-text").rows = isCoding ? 3 : 7;

  $("code-block").classList.toggle("hidden", !isCoding);
  if (isCoding) {
    ensureEditor();
    setCode(saved.code || question.starter_code || "");
    const output = $("code-output");
    output.textContent = saved.code_output || "";
    output.classList.toggle("hidden", !saved.code_output);
  }

  $("explain-text").value = saved.explanation || "";
  $("speak-status").textContent = "";

  $("prev-btn").disabled = index === 0;
  const isLast = index === state.questions.length - 1;
  $("next-btn").classList.toggle("hidden", isLast);
  $("submit-btn").classList.toggle("hidden", !isLast);

  refreshProgressDots();
}

$("prev-btn").addEventListener("click", async () => {
  await saveCurrentAnswer();
  if (state.index > 0) showQuestion(state.index - 1);
});

$("next-btn").addEventListener("click", async () => {
  await saveCurrentAnswer();
  if (state.index < state.questions.length - 1) showQuestion(state.index + 1);
});

$("submit-btn").addEventListener("click", async () => {
  const unanswered = state.questions.filter((q) => {
    const a = state.answers[q.id] || {};
    return !(a.answer || a.code || "").trim();
  }).length;
  const message = unanswered
    ? `${unanswered} question(s) have no answer. Finish the interview anyway?`
    : "Finish the interview and generate your scorecard?";
  if (!confirm(message)) return;
  await finishInterview("submitted");
});

/* ------------------------------------------------------------ code execution */

$("run-btn").addEventListener("click", async () => {
  const output = $("code-output");
  const button = $("run-btn");
  button.disabled = true;
  button.textContent = "Running...";
  output.classList.remove("hidden", "err");
  output.textContent = "Running your code...";

  try {
    const result = await api(`/api/session/${state.sessionId}/run-code`, {
      method: "POST",
      body: { code: getCode() },
    });
    const text =
      (result.stdout || "") +
      (result.stderr ? `\n--- stderr ---\n${result.stderr}` : "") ||
      "(no output - did you print anything?)";
    output.textContent = text;
    output.classList.toggle("err", Boolean(result.stderr) || result.exit_code !== 0);

    const question = state.questions[state.index];
    state.answers[question.id] = { ...(state.answers[question.id] || {}), code_output: text };
    await saveCurrentAnswer();
  } catch (err) {
    output.textContent = err.message;
    output.classList.add("err");
  } finally {
    button.disabled = false;
    button.textContent = "Run code";
  }
});

/* ------------------------------------------------------------ speech to text */

function buildRecognition() {
  const Engine = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Engine) return null;

  const recognition = new Engine();
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = "en-IN";

  recognition.onresult = (event) => {
    let finalText = "";
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      if (event.results[i].isFinal) finalText += event.results[i][0].transcript + " ";
    }
    if (finalText) {
      const box = $("explain-text");
      box.value = (box.value + " " + finalText).replace(/\s+/g, " ").trim();
    }
  };

  recognition.onerror = (event) => {
    if (event.error === "not-allowed" || event.error === "service-not-allowed") {
      $("speak-status").textContent = "Speech recognition blocked - type your explanation instead.";
      stopListening();
    }
  };

  recognition.onend = () => {
    if (state.listening) {
      try { recognition.start(); } catch (_) { /* restarting too fast */ }
    }
  };

  return recognition;
}

function stopListening() {
  state.listening = false;
  if (state.recognition) {
    try { state.recognition.stop(); } catch (_) { /* already stopped */ }
  }
  $("speak-btn").textContent = "Start explaining";
  $("speak-btn").classList.remove("live");
}

$("speak-btn").addEventListener("click", () => {
  if (state.listening) {
    stopListening();
    $("speak-status").textContent = "Stopped. You can edit the transcript above.";
    return;
  }

  if (!state.recognition) state.recognition = buildRecognition();
  if (!state.recognition) {
    $("speak-status").textContent =
      "Live transcription is not supported in this browser (use Chrome or Edge). " +
      "Type your explanation instead - it is still scored.";
    return;
  }

  state.listening = true;
  try {
    state.recognition.start();
    $("speak-btn").textContent = "Stop explaining";
    $("speak-btn").classList.add("live");
    $("speak-status").textContent = "Listening... speak clearly.";
  } catch (err) {
    state.listening = false;
    $("speak-status").textContent = "Could not start transcription: " + err.message;
  }
});

/* ------------------------------------------------------------ stage: results */

async function finishInterview(reason) {
  if (state.finished) return;
  state.finished = true;

  stopListening();
  proctor.stop();
  clearInterval(state.timerTick);
  window.removeEventListener("beforeunload", beforeUnload);
  await saveCurrentAnswer();
  stopRecording();
  if (document.fullscreenElement) document.exitFullscreen().catch(() => {});

  showStage("stage-result");
  $("scoring-spinner").classList.remove("hidden");
  $("scorecard").classList.add("hidden");
  $("result-actions").classList.add("hidden");
  $("camera-dock").classList.add("hidden");

  // Give the last recording chunk a moment to upload before scoring.
  await new Promise((resolve) => setTimeout(resolve, 800));

  try {
    const elapsed = Math.round((Date.now() - (state.startedAt || Date.now())) / 1000);
    const data = await api(`/api/session/${state.sessionId}/submit`, {
      method: "POST",
      body: { reason, elapsed_seconds: Math.max(0, elapsed) },
    });
    renderScorecard(data.scorecard, reason);
  } catch (err) {
    $("scoring-spinner").innerHTML =
      `<h2>Could not generate the scorecard</h2><p class="error">${escapeHtml(err.message)}</p>
       <p class="muted">Your answers and recording are saved under session
       <code>${escapeHtml(state.sessionId)}</code>.</p>`;
    $("result-actions").classList.remove("hidden");
  }
}

function renderScorecard(card, reason) {
  $("scoring-spinner").classList.add("hidden");
  const target = $("scorecard");
  target.classList.remove("hidden");
  $("result-actions").classList.remove("hidden");

  const ringColor = card.total_score >= 70 ? "#2fbf71" : card.total_score >= 50 ? "#e8b13a" : "#e4574c";
  const pillClass = card.total_score >= 70 ? "good" : card.total_score >= 50 ? "mid" : "bad";
  const integrity = card.integrity || { violation_count: 0, events: [], by_type: {} };

  const rows = card.breakdown.map((row) => `
    <tr>
      <td>
        <strong>Q${row.number}. ${escapeHtml(row.title)}</strong>
        <div class="muted small">${escapeHtml(row.type)}</div>
        <div class="small" style="margin-top:6px">${escapeHtml(row.feedback)}</div>
        ${row.red_flags && row.red_flags.length
          ? `<div class="small" style="color:#e4574c;margin-top:4px">&#9888; ${row.red_flags.map(escapeHtml).join("; ")}</div>`
          : ""}
      </td>
      <td class="num">${row.axes.correctness}/10</td>
      <td class="num">${row.axes.explanation}/10</td>
      <td class="num">${row.axes.communication}/10</td>
      <td class="num"><strong>${row.earned}</strong> / ${row.weight}</td>
    </tr>`).join("");

  const sections = Object.entries(card.section_scores || {}).map(
    ([name, value]) => `<li><strong>${escapeHtml(name)}</strong>: ${value.earned} / ${value.weight}</li>`
  ).join("");

  const bullets = (items, empty) =>
    items && items.length
      ? `<ul>${items.map((i) => `<li>${escapeHtml(i)}</li>`).join("")}</ul>`
      : `<p class="muted small">${empty}</p>`;

  const integrityBlock = integrity.violation_count
    ? `<div class="notice${integrity.terminated ? " bad" : ""}">
         <strong>${integrity.terminated
           ? "This interview was ended automatically by the proctor."
           : "Proctoring flags were recorded."}</strong>
         <ul style="margin:8px 0 0;padding-left:18px">
           ${Object.entries(integrity.by_type).map(([label, n]) =>
             `<li>${escapeHtml(label)} &times; ${n}</li>`).join("")}
         </ul>
         <div class="muted small" style="margin-top:8px">
           ${integrity.violation_count} flag(s) in total. Flags are shown to the reviewer;
           they do not directly change the marks below.
         </div>
       </div>`
    : `<div class="notice ok"><strong>No suspicious activity was recorded.</strong></div>`;

  target.innerHTML = `
    <div class="score-hero">
      <div class="score-ring" style="--pct:${card.total_score}%;--ring-color:${ringColor}">
        <div class="inner"><div><b>${card.total_score}</b><span>out of 100</span></div></div>
      </div>
      <div>
        <h2>Interview scorecard</h2>
        ${state.fullName ? `<p class="candidate-name">${escapeHtml(state.fullName)}</p>` : ""}
        <p class="muted">${escapeHtml(state.email || "")} &middot; session
          <code>${escapeHtml(state.sessionId)}</code>${reason === "time_expired" ? " &middot; time expired" : ""}</p>
        <p><span class="pill ${pillClass}">${escapeHtml(card.grade)}</span>
           <span class="pill ${pillClass}">${escapeHtml(card.recommendation)}</span></p>
        <ul class="muted small" style="padding-left:18px">${sections}</ul>
      </div>
    </div>

    ${integrityBlock}

    <h3>Summary</h3>
    <p>${escapeHtml(card.summary)}</p>

    <div class="two-col">
      <div><h3>Strengths</h3>${bullets(card.strengths, "None recorded.")}</div>
      <div><h3>Areas to improve</h3>${bullets(card.improvements, "None recorded.")}</div>
    </div>

    <h3>Question breakdown</h3>
    <table class="breakdown">
      <thead><tr>
        <th>Question &amp; feedback</th><th class="num">Correct</th>
        <th class="num">Explain</th><th class="num">Comms</th><th class="num">Score</th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table>

    ${card.engine !== "claude"
      ? `<div class="notice"><strong>Heuristic scoring only.</strong>
         ${escapeHtml(card.engine_error || "")} - set ANTHROPIC_API_KEY and re-run scoring for a real review.</div>`
      : ""}

    <p class="muted small" style="margin-top:22px">
      Session recording:
      <a href="/api/session/${encodeURIComponent(state.sessionId)}/recording" target="_blank">download .webm</a>
    </p>
  `;
}
