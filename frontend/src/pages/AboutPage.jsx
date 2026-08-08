import NavBar from '../components/NavBar'
import rzwireLogo from '../assets/brands/rzwire-logo-theme-5.png'
import mgcLogo from '../assets/brands/mgc-coin-logo.png'
import rankingLogo from '../assets/brands/ranking-platform-logo.png'
import oasisLogo from '../assets/brands/oasis-coin-logo.png'
import jewelryLogo from '../assets/brands/jewelry-coin-logo.png'
import { Link } from '../router'
import './AboutPage.css'

const BRANDS = [
  {
    name: 'MGC Coin',
    label: 'Play economies',
    description: 'Gaming utility, participation, progression, and the economy around play.',
    logo: mgcLogo,
    color: '#f2c84b',
  },
  {
    name: 'Ranking Platform',
    label: 'Proof of performance',
    description: 'Competition, reputation, achievements, tournaments, and player value.',
    logo: rankingLogo,
    color: '#ff4f9a',
  },
  {
    name: 'Oasis Coin',
    label: 'Connected systems',
    description: 'Long-horizon infrastructure, trust, resilience, and digital ecosystems.',
    logo: oasisLogo,
    color: '#e0e5ef',
  },
  {
    name: 'Jewelry Coin',
    label: 'Creative ownership',
    description: 'Digital creation, verifiable ownership, real utility, and wearable value.',
    logo: jewelryLogo,
    color: '#b795ff',
  },
]

const WORKFLOW = [
  ['01', 'Listen', 'Bring trusted RSS publishers and Telegram channels into a single live signal stream.'],
  ['02', 'Understand', 'Analyze relevance, quality, risk, and opportunity before a story reaches a brand lane.'],
  ['03', 'Route', 'Match every useful signal to the brand whose audience, goals, and voice it serves best.'],
  ['04', 'Create', 'Build platform-ready copy and art direction without flattening four identities into one.'],
  ['05', 'Control', 'Review, edit, save, schedule, and publish from one accountable human-controlled workspace.'],
]

const GOALS = [
  ['Clarity', 'Reduce noise and make the next editorial decision obvious.'],
  ['Consistency', 'Protect each brand voice across every channel and every operator.'],
  ['Velocity', 'Move from source to approved creative without sacrificing judgment.'],
  ['Memory', 'Keep decisions, saved stories, schedules, and activity connected.'],
]

export default function AboutPage() {
  return (
    <div className="about-page">
      <NavBar />

      <main className="about-main">
        <section className="about-hero">
          <div className="about-hero__mesh" aria-hidden="true" />

          <div className="about-hero__copy">
            <div className="about-kicker"><span /> RZWire editorial operating system</div>
            <h1>Signals in.<br /><em>Stories out.</em></h1>
            <p className="about-hero__lead">
              RZWire is the private intelligence and publishing workspace behind six distinct digital brands.
              It turns a constant flow of news into deliberate, brand-ready communication.
            </p>
            <div className="about-hero__actions">
              <Link className="about-button about-button--primary" to="/multimedia">Enter the newsroom <span>→</span></Link>
              <a className="about-button about-button--quiet" href="#how-it-works">See how it works</a>
            </div>
            <div className="about-hero__proof" aria-label="RZWire capabilities">
              <span>RSS + Telegram intelligence</span>
              <span>AI-assisted editorial routing</span>
              <span>Human approval and distribution</span>
            </div>
          </div>

          <div className="about-console" aria-label="Illustration of the RZWire editorial system">
            <div className="about-console__topbar">
              <div className="about-console__identity"><img src={rzwireLogo} alt="" /><span>RZWire / live desk</span></div>
              <div className="about-console__status"><i /> Monitoring sources</div>
            </div>

            <div className="about-console__sources">
              <span>RSS publishers</span><span>Telegram channels</span><span>Market signals</span>
            </div>

            <div className="about-console__signal">
              <div className="signal-mark"><span /><span /><span /></div>
              <div><small>Editorial signal</small><strong>Story worth routing detected</strong></div>
              <b>98</b>
            </div>

            <div className="about-console__analysis">
              <div className="analysis-heading"><span>RZWire intelligence pass</span><small>Relevance · quality · risk</small></div>
              <div className="analysis-track"><i /></div>
              <div className="analysis-notes"><span>Context enriched</span><span>Duplicate checked</span><span>Brand fit mapped</span></div>
            </div>

            <div className="about-console__route-label"><span>Route to the right world</span><i /></div>
            <div className="about-console__brands">
              {BRANDS.map(brand => (
                <div className="console-brand" style={{ '--brand-color': brand.color }} key={brand.name}>
                  <img src={brand.logo} alt="" />
                  <span>{brand.name}</span>
                </div>
              ))}
            </div>

            <div className="console-float console-float--one"><span>4</span> protected identities</div>
            <div className="console-float console-float--two"><i /> Human in control</div>
          </div>
        </section>

        <section className="about-statement">
          <div className="about-section-index">01 / Purpose</div>
          <div className="about-statement__body">
            <p className="about-eyebrow">Why RZWire exists</p>
            <h2>Information is everywhere.<br />Direction is rare.</h2>
            <p>
              RZWire gives one editorial team a reliable way to observe the market, recognize what matters,
              and translate it into communication each brand can genuinely own. The goal is not more content.
              The goal is better decisions, expressed with speed and precision.
            </p>
          </div>
        </section>

        <section className="about-bento" aria-label="Core RZWire functions">
          <article className="bento-card bento-card--radar">
            <div className="bento-icon bento-icon--radar"><i /><i /><i /></div>
            <span className="about-card-number">A / Source intelligence</span>
            <h3>One radar for a noisy world.</h3>
            <p>Approved news sites and public channels become a focused editorial feed instead of scattered tabs and disconnected alerts.</p>
          </article>
          <article className="bento-card bento-card--brain">
            <div className="bento-route" aria-hidden="true"><i /><i /><i /><i /></div>
            <span className="about-card-number">B / Editorial intelligence</span>
            <h3>Machines assist.<br />Editors decide.</h3>
            <p>AI helps score, compare, enrich, route, write, and art-direct. Judgment and accountability stay with the operator.</p>
          </article>
          <article className="bento-card bento-card--output">
            <div className="output-lines" aria-hidden="true"><i /><i /><i /></div>
            <span className="about-card-number">C / Controlled output</span>
            <h3>From draft to distribution.</h3>
            <p>Create channel-aware copy and imagery, keep useful work, schedule deliberately, and publish only when it is ready.</p>
          </article>
        </section>

        <section className="about-workflow" id="how-it-works">
          <div className="about-workflow__intro">
            <div className="about-section-index">02 / System</div>
            <p className="about-eyebrow">How it works</p>
            <h2>A newsroom pipeline built around intent.</h2>
            <p>Every stage answers a different question, so speed never has to erase context.</p>
          </div>
          <div className="about-workflow__steps">
            {WORKFLOW.map(([number, title, text], index) => (
              <article className="workflow-step" key={number}>
                <div className="workflow-step__rail"><span>{number}</span>{index < WORKFLOW.length - 1 && <i />}</div>
                <div><h3>{title}</h3><p>{text}</p></div>
              </article>
            ))}
          </div>
        </section>

        <section className="about-brands">
          <div className="about-brands__heading">
            <div>
              <div className="about-section-index">03 / Brand architecture</div>
              <p className="about-eyebrow">One wire. Four worlds.</p>
              <h2>Shared intelligence.<br />Independent identities.</h2>
            </div>
            <p>RZWire provides the infrastructure, but it never makes the brands look or sound interchangeable. Each lane has its own editorial logic, visual families, vocabulary, and audience promise.</p>
          </div>

          <div className="about-brand-grid">
            {BRANDS.map((brand, index) => (
              <article className="about-brand-card" style={{ '--brand-color': brand.color }} key={brand.name}>
                <div className="about-brand-card__top"><span>0{index + 1}</span><i /></div>
                <div className="about-brand-card__logo"><img src={brand.logo} alt={`${brand.name} logo`} /></div>
                <p className="about-brand-card__label">{brand.label}</p>
                <h3>{brand.name}</h3>
                <p>{brand.description}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="about-control">
          <div className="about-control__visual" aria-hidden="true">
            <div className="control-ring control-ring--outer" /><div className="control-ring control-ring--inner" />
            <div className="control-core"><img src={rzwireLogo} alt="" /><span>Editorial control</span></div>
            <span className="control-tag control-tag--review">Review</span>
            <span className="control-tag control-tag--history">History</span>
            <span className="control-tag control-tag--schedule">Schedule</span>
            <span className="control-tag control-tag--publish">Publish</span>
          </div>
          <div className="about-control__copy">
            <div className="about-section-index">04 / Governance</div>
            <p className="about-eyebrow">Human control is the feature</p>
            <h2>Automation without autopilot.</h2>
            <p>RZWire accelerates the work that benefits from machines while keeping consequential choices visible to people.</p>
            <ul>
              <li><span>01</span><div><strong>Review before release</strong><small>Copy, imagery, timing, and destination remain inspectable.</small></div></li>
              <li><span>02</span><div><strong>Boundaries by brand</strong><small>Rules and Art Directors prevent identity drift across the ecosystem.</small></div></li>
              <li><span>03</span><div><strong>A workspace with memory</strong><small>Saved work, activity, schedules, and decisions stay connected to the account.</small></div></li>
            </ul>
          </div>
        </section>

        <section className="about-goals">
          <div className="about-goals__intro">
            <div className="about-section-index">05 / Goals</div>
            <p className="about-eyebrow">What success looks like</p>
            <h2>A stronger editorial system with every signal.</h2>
          </div>
          <div className="about-goals__grid">
            {GOALS.map(([title, text], index) => (
              <article key={title}><span>0{index + 1}</span><h3>{title}</h3><p>{text}</p></article>
            ))}
          </div>
        </section>

        <section className="about-final-cta">
          <div className="about-final-cta__mark"><img src={rzwireLogo} alt="RZWire" /></div>
          <div>
            <p className="about-eyebrow">The newsroom is live</p>
            <h2>Find the signal.<br />Shape the story.</h2>
          </div>
          <Link className="about-button about-button--primary" to="/multimedia">Open Multimedia <span>→</span></Link>
        </section>
      </main>

      <footer className="about-footer">
        <img src={rzwireLogo} alt="RZWire" />
        <p>Private intelligence and publishing for the RZ Token Family.</p>
        <span>© 2026 RZWire</span>
      </footer>
    </div>
  )
}
