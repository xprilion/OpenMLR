import { useNavigate } from 'react-router-dom';

const IS_PROD = window.location.hostname === 'openmlr.dev';
const DOCS_URL = 'https://openmlr.dev';

export function LandingPage() {
  const navigate = useNavigate();

  const handleGetStarted = () => {
    if (IS_PROD) {
      window.location.href = `${DOCS_URL}/setup`;
    } else {
      navigate('/login');
    }
  };

  return (
    <div className="landing">
      <div className="landing-content">
        <h1 className="landing-title">OpenMLR</h1>
        <p className="landing-tagline">
          Your ML research intern. Plans tasks, reads papers, writes drafts,
          and runs experiments — end to end.
        </p>

        <div className="landing-features">
          <div className="landing-feature">
            <span className="lf-icon">P</span>
            <div>
              <strong>Plan</strong>
              <span>Structured questions, task breakdown, scope clarification</span>
            </div>
          </div>
          <div className="landing-feature">
            <span className="lf-icon">R</span>
            <div>
              <strong>Research</strong>
              <span>ArXiv, OpenAlex, citation graphs, code search</span>
            </div>
          </div>
          <div className="landing-feature">
            <span className="lf-icon">W</span>
            <div>
              <strong>Write</strong>
              <span>Section-by-section drafting with bibliography management</span>
            </div>
          </div>
          <div className="landing-feature">
            <span className="lf-icon">E</span>
            <div>
              <strong>Execute</strong>
              <span>Docker-isolated code execution, SSH remotes, Modal cloud</span>
            </div>
          </div>
        </div>

        <div className="landing-actions">
          <button className="landing-btn landing-btn-primary" onClick={handleGetStarted}>
            Get Started
          </button>
          <a className="landing-btn landing-btn-secondary" href={DOCS_URL} target="_blank" rel="noopener noreferrer">
            Read Docs
          </a>
        </div>

        <p className="landing-footer">
          Open source &middot; Self-hosted &middot; MIT License
        </p>
      </div>
    </div>
  );
}
