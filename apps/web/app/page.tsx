import { AudioRecorder } from "./components/audio-recorder";

export default function Home() {
  return (
    <main>
      <section className="hero" aria-labelledby="page-title">
        <p className="eyebrow">Private communication coaching</p>
        <h1 id="page-title">Project Voice</h1>
        <p className="summary">
          Build clearer, calmer, more confident communication—on your own terms.
        </p>
        <div className="status" role="status">
          <span className="statusDot" aria-hidden="true" />
          Your recordings stay under your control.
        </div>
      </section>
      <AudioRecorder />
    </main>
  );
}
