import NavBar from '../components/NavBar'
import rzwireLogo from '../assets/brands/rzwire-logo.png'
import mgcLogo from '../assets/brands/mgc-coin-logo.png'
import rankingLogo from '../assets/brands/ranking-platform-logo.png'
import oasisLogo from '../assets/brands/oasis-coin-logo.png'
import jewelryLogo from '../assets/brands/jewelry-coin-logo.png'
import { Link } from '../router'
import './AboutPage.css'
import './AboutPageFixes.css'

const BRANDS = [
  { name: 'MGC Coin', logo: mgcLogo, color: '#f2c84b', position: 'brand-node--mgc' },
  { name: 'Ranking Platform', logo: rankingLogo, color: '#ff4f9a', position: 'brand-node--ranking' },
  { name: 'Oasis Coin', logo: oasisLogo, color: '#d7dbe8', position: 'brand-node--oasis' },
  { name: 'Jewelry Coin', logo: jewelryLogo, color: '#a989ff', position: 'brand-node--jewelry' },
]

const WORKFLOW = [
  ['01', 'Discover', 'Keep every approved RSS and Telegram news source in one live workspace.'],
  ['02', 'Route', 'Match each story to the right brand and platform lane.'],
  ['03', 'Create', 'Generate brand-aware copy and imagery with four distinct Art Directors.'],
  ['04', 'Review', 'Approve, save, and schedule locally before any external connection is enabled.'],
]

export default function AboutPage() {
  return (
    <div className="about-page">
      <NavBar />
      <main>
        <section className="about-hero">
          <div className="wire-field" aria-hidden="true">
            <div className="wire-orbit wire-orbit--one" /><div className="wire-orbit wire-orbit--two" />
            <div className="wire-line wire-line--north" /><div className="wire-line wire-line--east" />
            <div className="wire-line wire-line--south" /><div className="wire-line wire-line--west" />
            <div className="wire-core"><span className="wire-core__glow" /><img src={rzwireLogo} alt="" /></div>
            {BRANDS.map(brand => (
              <div className={`brand-node ${brand.position}`} style={{ '--brand-color': brand.color }} key={brand.name}>
                <span className="brand-node__halo" /><img src={brand.logo} alt="" /><strong>{brand.name}</strong>
              </div>
            ))}
          </div>
          <div className="about-hero__content">
            <span className="about-kicker"><i /> RZWire Publishing Workspace</span>
            <h1>One newsroom.<br /><em>Four distinct worlds.</em></h1>
            <p>RZWire turns trusted news sources into brand-ready stories for MGC Coin, Ranking Platform, Oasis Coin, and Jewelry Coin.</p>
            <Link className="about-primary-action" to="/multimedia">Open Multimedia <span>→</span></Link>
          </div>
        </section>
        <section className="about-section about-section--intro">
          <div className="about-section__heading"><span>Built for focus</span><h2>A private publishing system with a clear editorial boundary.</h2></div>
          <p className="about-lede">RZWire brings sourcing, analysis, brand routing, social copy, image direction, scheduling, account history, and workspace guidance into one dark, fast interface. Every brand keeps its own voice and visual language while the workspace stays unmistakably RZWire.</p>
        </section>
        <section className="about-section">
          <div className="about-section__heading"><span>The workflow</span><h2>From signal to approved story.</h2></div>
          <div className="workflow-grid">{WORKFLOW.map(([number, title, text]) => <article className="workflow-card" key={number}><small>{number}</small><h3>{title}</h3><p>{text}</p></article>)}</div>
        </section>
        <section className="about-section">
          <div className="about-section__heading"><span>Brand constellation</span><h2>Shared infrastructure. Independent identities.</h2></div>
          <div className="brand-grid">{BRANDS.map(brand => <article className="brand-card" style={{ '--brand-color': brand.color }} key={brand.name}><div className="brand-card__image"><img src={brand.logo} alt={`${brand.name} logo`} /></div><h3>{brand.name}</h3><p>Dedicated editorial rules, visual families, prompts, and brand-safe production guidance.</p></article>)}</div>
        </section>
        <section className="about-cta">
          <img src={rzwireLogo} alt="RZWire" /><div><span>Local-first by design</span><h2>Build, review, then connect.</h2><p>Publishing and Google Sheets remain disabled until the new RZWire integrations are supplied.</p></div>
        </section>
      </main>
      <footer className="about-footer"><img src={rzwireLogo} alt="RZWire" /><span>© 2026 RZWire. Private multi-brand publishing.</span></footer>
    </div>
  )
}
