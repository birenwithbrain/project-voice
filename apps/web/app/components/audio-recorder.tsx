"use client";

import { ChangeEvent, useEffect, useRef, useState } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

type RecorderState = "idle" | "recording" | "ready" | "uploading" | "complete" | "error";

function preferredMimeType(): string | undefined {
  return ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus"].find((type) =>
    MediaRecorder.isTypeSupported(type),
  );
}

export function AudioRecorder() {
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const startedAtRef = useRef<number>(0);
  const [audio, setAudio] = useState<Blob | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [durationMs, setDurationMs] = useState<number | null>(null);
  const [savedSessionId, setSavedSessionId] = useState<string | null>(null);
  const [state, setState] = useState<RecorderState>("idle");
  const [message, setMessage] = useState("Choose Record to begin a private practice session.");

  useEffect(() => {
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, [audioUrl]);

  function setAudioPreview(blob: Blob, duration: number | null) {
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudio(blob);
    setAudioUrl(URL.createObjectURL(blob));
    setDurationMs(duration);
    setState("ready");
    setMessage("Recording ready. Listen once, then save it privately.");
  }

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = preferredMimeType();
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      streamRef.current = stream;
      recorderRef.current = recorder;
      chunksRef.current = [];
      startedAtRef.current = Date.now();
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        stream.getTracks().forEach((track) => track.stop());
        setAudioPreview(blob, Math.max(1, Date.now() - startedAtRef.current));
      };
      recorder.start();
      setState("recording");
      setMessage("Recording locally in your browser. Stop when you are ready.");
    } catch {
      setState("error");
      setMessage("Microphone access was not granted. Check your browser permission and try again.");
    }
  }

  function stopRecording() {
    recorderRef.current?.stop();
  }

  function useUploadedFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("audio/")) {
      setState("error");
      setMessage("Choose an audio file such as WebM, MP3, M4A, WAV, or OGG.");
      return;
    }
    setAudioPreview(file, null);
  }

  async function saveRecording() {
    if (!audio) return;
    setState("uploading");
    setMessage("Saving your recording privately…");
    try {
      const createResponse = await fetch(`${API_BASE_URL}/speech-sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind: "practice", title: "Practice session" }),
      });
      if (!createResponse.ok) throw new Error("Could not create a practice session.");
      const speechSession: { id: string } = await createResponse.json();
      const formData = new FormData();
      formData.append("file", audio, "practice-recording.webm");
      if (durationMs !== null) formData.append("duration_ms", String(durationMs));
      const uploadResponse = await fetch(`${API_BASE_URL}/speech-sessions/${speechSession.id}/audio`, {
        method: "POST",
        body: formData,
      });
      if (!uploadResponse.ok) throw new Error("Could not save the recording.");
      setSavedSessionId(speechSession.id);
      setState("complete");
      setMessage("Saved privately. Run local analysis and review coaching in your session report.");
    } catch {
      setState("error");
      setMessage("The recording was not saved. Keep this page open and try again once the API and database are running.");
    }
  }

  return (
    <section className="recorder" aria-labelledby="recorder-title">
      <div>
        <p className="eyebrow">Practice session</p>
        <h2 id="recorder-title">Give your voice some room.</h2>
        <p className="recorderMessage">{message}</p>
      </div>
      <div className="recorderControls">
        {state !== "recording" ? (
          <button type="button" onClick={startRecording} disabled={state === "uploading"}>
            Record
          </button>
        ) : (
          <button type="button" onClick={stopRecording} className="recordingButton">
            Stop recording
          </button>
        )}
        <label className="uploadLabel">
          Or upload audio
          <input type="file" accept="audio/*" onChange={useUploadedFile} disabled={state === "uploading"} />
        </label>
      </div>
      {audioUrl && <audio className="audioPreview" controls src={audioUrl} />}
      {state === "ready" && (
        <button type="button" className="saveButton" onClick={saveRecording}>
          Save practice session
        </button>
      )}
      {state === "complete" && savedSessionId && (
        <a className="reportLink" href={`/sessions/${savedSessionId}`}>
          Open session report <span aria-hidden="true">→</span>
        </a>
      )}
    </section>
  );
}
