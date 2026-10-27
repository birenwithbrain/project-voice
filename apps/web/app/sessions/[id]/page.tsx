"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

type Priority = "low" | "medium" | "high";
type CoachingPoint = { title: string; evidence: string; priority: Priority };
type CoachingImprovement = CoachingPoint & { why_it_matters: string };
type RecommendedExercise = { title: string; instructions: string; duration_minutes: number };
type CoachingResult = {
  strengths: CoachingPoint[];
  improvements: CoachingImprovement[];
  recommended_exercises: RecommendedExercise[];
  next_focus: string;
};
type Metric = { metric_code: string; value: number; unit: string };
type SessionReport = {
  id: string;
  kind: string;
  status: string;
  title: string | null;
  created_at: string;
  transcript: string | null;
  metrics: Metric[];
  coaching_report: CoachingResult | null;
  coaching_model: string | null;
  coaching_created_at: string | null;
};

function prettyMetricName(code: string) {
  return code.replaceAll("_", " ");
}

function metricDisplay(metric: Metric) {
  if (metric.metric_code === "filler_rate") return `${(metric.value * 100).toFixed(1)}%`;
  if (metric.value === 0) return "0";
  return Number(metric.value.toFixed(2)).toLocaleString();
}

function readableEvidence(evidence: string) {
  const metric = evidence.match(/metric:([a-z0-9_]+)\s+value:([-+]?(?:\d+(?:\.\d*)?|\.\d+))\s+unit:([a-z0-9_/%]+)/i);
  if (metric) {
    return `${prettyMetricName(metric[1])}: ${Number(metric[2]).toLocaleString()} ${metric[3].replaceAll("_", " ")}`;
  }
  const quote = evidence.match(/transcript_quote:\s*["“](.*?)["”]/s);
  return quote ? `Transcript: “${quote[1]}”` : evidence;
}

export default function SessionReportPage() {
  const params = useParams<{ id: string }>();
  const sessionId = params.id;
  const [report, setReport] = useState<SessionReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState<"analysis" | "coaching" | null>(null);
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadReport = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/speech-sessions/${sessionId}/report`);
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail ?? "Could not load this session report.");
      setReport(body as SessionReport);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load this session report.");
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    void loadReport();
  }, [loadReport]);

  async function runLocalAnalysis() {
    setWorking("analysis");
    setError(null);
    try {
      for (const step of ["preprocess", "transcribe", "analyze"]) {
        const response = await fetch(`${API_BASE_URL}/speech-sessions/${sessionId}/${step}`, { method: "POST" });
        const body = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(body.detail ?? `Local ${step} failed.`);
      }
      await loadReport();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Local analysis could not be completed.");
    } finally {
      setWorking(null);
    }
  }

  async function generateCoaching() {
    if (!consent) return;
    setWorking("coaching");
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/speech-sessions/${sessionId}/coach`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ consent: true }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail ?? "Coaching could not be completed.");
      setConsent(false);
      await loadReport();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gemini coaching could not be completed.");
    } finally {
      setWorking(null);
    }
  }

  return (
    <main className="reportPage">
      <div className="reportHeader">
        <div>
          <a className="backLink" href="/">← Back to practice</a>
          <p className="eyebrow" style={{ marginTop: "1.5rem" }}>Session report</p>
          <h1 className="reportTitle">Your speaking, understood.</h1>
          <p className="reportMeta">
            {report?.title ?? "Practice session"}{report ? ` · ${report.kind} · ${report.status}` : ""}
          </p>
        </div>
        <button type="button" className="reportButtonSecondary" onClick={() => void loadReport()} disabled={loading || working !== null}>
          Refresh report
        </button>
      </div>

      {error && <div className="reportError" role="alert">{error}</div>}
      {loading && <p className="reportMeta" role="status">Loading session report…</p>}

      {report && (
        <>
          <section className="reportPanel">
            <h2>Local analysis</h2>
            <p>
              Your recording is processed locally. This step normalizes the audio, transcribes it with local Whisper,
              and calculates deterministic speaking metrics. It does not call Gemini.
            </p>
            <div className="reportActions">
              <button type="button" onClick={() => void runLocalAnalysis()} disabled={working !== null}>
                {working === "analysis" ? "Analyzing locally…" : report.transcript && report.metrics.length ? "Refresh local analysis" : "Run local analysis"}
              </button>
              <span className="reportMeta">{report.metrics.length} metrics available</span>
            </div>
          </section>

          {report.metrics.length > 0 && (
            <section className="reportPanel" aria-labelledby="metrics-heading">
              <h2 id="metrics-heading">Speaking metrics</h2>
              <div className="reportGrid">
                {report.metrics.map((metric) => (
                  <article className="metricCard" key={metric.metric_code}>
                    <span className="metricName">{prettyMetricName(metric.metric_code)}</span>
                    <strong className="metricValue">{metricDisplay(metric)}</strong>
                    <span className="metricUnit">{metric.metric_code === "filler_rate" ? "of spoken words" : metric.unit.replaceAll("_", " ")}</span>
                  </article>
                ))}
              </div>
            </section>
          )}

          {report.transcript && (
            <section className="reportPanel">
              <h2>Transcript</h2>
              <p className="reportMeta">Stored locally. Only sent to Gemini when you explicitly consent below.</p>
              <p className="transcriptText">{report.transcript}</p>
            </section>
          )}

          <section className="reportPanel">
            <h2>AI coach</h2>
            <p>
              Gemini receives the transcript, calculated metrics, and saved communication goal/context only.
              Raw audio is never uploaded to the AI provider.
            </p>
            {!report.transcript || !report.metrics.length ? (
              <p>Run local analysis before generating coaching.</p>
            ) : (
              <>
                <label className="consentRow">
                  <input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} disabled={working !== null} />
                  <span>I consent to send this session’s transcript, deterministic metrics, and saved goal/context to Google Gemini for coaching.</span>
                </label>
                <div className="reportActions">
                  <button type="button" onClick={() => void generateCoaching()} disabled={!consent || working !== null}>
                    {working === "coaching" ? "Generating coaching…" : report.coaching_report ? "Regenerate coaching" : "Generate Gemini coaching"}
                  </button>
                  {report.coaching_model && <span className="reportMeta">Model: {report.coaching_model}</span>}
                </div>
              </>
            )}
          </section>

          {report.coaching_report && (
            <>
              <section className="reportPanel">
                <h2>Strengths</h2>
                {report.coaching_report.strengths.length === 0 ? <p>No strengths were returned for this session.</p> : (
                  <ul className="coachingList">
                    {report.coaching_report.strengths.map((point, index) => (
                      <li className="coachingItem" key={`strength-${index}`}>
                        <span className="priority">{point.priority} priority</span>
                        <h3>{point.title}</h3>
                        <p className="evidence">{readableEvidence(point.evidence)}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
              <section className="reportPanel">
                <h2>Areas to improve</h2>
                {report.coaching_report.improvements.length === 0 ? <p>No specific improvements were flagged. Keep practicing consistently.</p> : (
                  <ul className="coachingList">
                    {report.coaching_report.improvements.map((point, index) => (
                      <li className="coachingItem" key={`improvement-${index}`}>
                        <span className="priority">{point.priority} priority</span>
                        <h3>{point.title}</h3>
                        <p>{point.why_it_matters}</p>
                        <p className="evidence">{readableEvidence(point.evidence)}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
              <section className="reportPanel">
                <h2>Recommended exercises</h2>
                <ul className="coachingList">
                  {report.coaching_report.recommended_exercises.map((exercise, index) => (
                    <li className="coachingItem" key={`exercise-${index}`}>
                      <span className="priority">{exercise.duration_minutes} minute practice</span>
                      <h3>{exercise.title}</h3>
                      <p>{exercise.instructions}</p>
                    </li>
                  ))}
                </ul>
              </section>
              <section className="reportPanel">
                <h2>Your next focus</h2>
                <p>{report.coaching_report.next_focus}</p>
                {report.coaching_created_at && <p className="reportMeta">Generated {new Date(report.coaching_created_at).toLocaleString()}</p>}
              </section>
            </>
          )}
        </>
      )}
    </main>
  );
}
