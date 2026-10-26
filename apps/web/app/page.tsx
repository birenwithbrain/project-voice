const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

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
          Foundation ready. Audio sessions begin in Phase 3.
        </div>
      </section>
      <section className="nextStep" aria-labelledby="next-step-title">
        <p className="eyebrow">Next up</p>
        <h2 id="next-step-title">Private data foundation</h2>
        <p>
          Phase 2 will add the data model for sessions, transcripts, metrics, exercises,
          and your coaching profile.
        </p>
        <a href={`${API_BASE_URL}/health/live`} target="_blank" rel="noreferrer">
          Check API health
        </a>
      </section>
    </main>
  );
}
