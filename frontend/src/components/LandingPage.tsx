import { useNavigate } from 'react-router-dom';

const DOCS_URL = 'https://openmlr.dev';
const GITHUB_URL = 'https://github.com/xprilion/OpenMLR';

export function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="landing">
      <div className="landing-content">
        <h1 className="landing-title">OpenMLR</h1>
        
        <p className="landing-hook">
          Built for ML researchers who are tired of context-switching.
        </p>
        
        <p className="landing-tagline">
          Search papers, take notes, write drafts, run experiments — all in one conversation.
        </p>

        <div className="landing-features">
          <div className="landing-feature">
            <span className="lf-icon">P</span>
            <div>
              <strong>Plan</strong>
              <span>Asks the right questions before diving in</span>
            </div>
          </div>
          <div className="landing-feature">
            <span className="lf-icon">R</span>
            <div>
              <strong>Research</strong>
              <span>OpenAlex, ArXiv, citation graphs, full papers</span>
            </div>
          </div>
          <div className="landing-feature">
            <span className="lf-icon">W</span>
            <div>
              <strong>Write</strong>
              <span>Section-by-section drafting with auto-citations</span>
            </div>
          </div>
          <div className="landing-feature">
            <span className="lf-icon">E</span>
            <div>
              <strong>Execute</strong>
              <span>Docker-isolated code, SSH remotes, Modal cloud</span>
            </div>
          </div>
        </div>

        <div className="landing-actions">
          <button className="landing-btn landing-btn-primary" onClick={() => navigate('/login')}>
            Get Started
          </button>
          <a className="landing-btn landing-btn-secondary" href={DOCS_URL} target="_blank" rel="noopener noreferrer">
            Read Docs
          </a>
          <a className="landing-btn landing-btn-tertiary" href={GITHUB_URL} target="_blank" rel="noopener noreferrer">
            GitHub
          </a>
        </div>

        <p className="landing-footer">
          Open source · Self-hosted · MIT License
        </p>
      </div>
    </div>
  );
}
