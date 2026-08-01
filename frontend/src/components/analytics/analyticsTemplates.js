import phoneA from '../../assets/analytics-concepts/phone-a.png'
import phoneB from '../../assets/analytics-concepts/phone-b.png'
import phoneC from '../../assets/analytics-concepts/phone-c.png'
import desktopA from '../../assets/analytics-concepts/desktop-a.png'
import desktopB from '../../assets/analytics-concepts/desktop-b.png'
import desktopC from '../../assets/analytics-concepts/desktop-c.png'
import growthA from '../../assets/analytics-concepts/growth-a.png'
import growthB from '../../assets/analytics-concepts/growth-b.png'
import growthC from '../../assets/analytics-concepts/growth-c.png'
import contrastA from '../../assets/analytics-concepts/contrast-a.png'
import contrastB from '../../assets/analytics-concepts/contrast-b.png'
import contrastC from '../../assets/analytics-concepts/contrast-c.png'
import cardsA from '../../assets/analytics-concepts/cards-a.png'
import cardsB from '../../assets/analytics-concepts/cards-b.png'
import cardsC from '../../assets/analytics-concepts/cards-c.png'
import combinedA from '../../assets/analytics-concepts/combined-a.png'
import combinedB from '../../assets/analytics-concepts/combined-b.png'
import combinedC from '../../assets/analytics-concepts/combined-c.png'

function variant(id, conceptLabel, name, description, image, stylePrompt) {
  return {id, conceptLabel, name, description, image, stylePrompt}
}

export const TEMPLATE_CATEGORIES = [
  {id:'phone', name:'Phone Market View', description:'Mobile market presentation', variants:[
    variant('phone-centered', 'A', 'Centered phone', 'A centered premium phone with a complete market view.', phoneA, 'Centered full-height phone, bold header above, restrained side callouts, generous brand-colored negative space.'),
    variant('phone-split-stat', 'B', 'Split-stat phone', 'Editorial phone with exact result callouts at the side.', phoneB, 'Angled editorial phone, large performance statement, asymmetric side statistics, cinematic brand atmosphere.'),
    variant('phone-editorial', 'C', 'Compact editorial phone', 'A close, dramatic phone composition for fast reading.', phoneC, 'Tight cropped phone, oversized market headline, compact comparison labels, high-impact mobile editorial composition.'),
  ]},
  {id:'laptop', name:'Laptop Dashboard', description:'Desktop market presentation', variants:[
    variant('laptop-cinematic', 'A', 'Cinematic laptop', 'Frontal laptop on a dramatic chart-focused stage.', desktopA, 'Centered frontal laptop, premium atmospheric stage, strong headline above, small verified data strip below.'),
    variant('laptop-editorial', 'B', 'Editorial laptop', 'Angled laptop with calm editorial spacing.', desktopB, 'Angled laptop, spacious editorial hierarchy, atmospheric brand environment, chart dominant inside the screen.'),
    variant('laptop-wide', 'C', 'Wide dashboard laptop', 'Desk-set laptop with a wider multi-series presentation.', desktopC, 'Laptop on a realistic editorial desk, wide chart screen, soft environmental lighting and restrained header/footer.'),
  ]},
  {id:'growth', name:'Growth Spotlight', description:'Focused performance story', variants:[
    variant('growth-card', 'A', 'Performance card', 'Headline, verified chart and two exact result strips.', growthA, 'Protected chart card, concise headline, start/end and movement strips, crisp brand-owned information hierarchy.'),
    variant('growth-hero', 'B', 'Growth hero', 'Large percentage-led hero with a dominant chart.', growthB, 'Oversized verified percentage, large protected chart, energetic but refined brand gradient and compact footer.'),
    variant('growth-milestone', 'C', 'Milestone result', 'Editorial headline and a refined milestone chart.', growthC, 'Editorial headline, premium serif/sans contrast, protected chart panel, spacious luxury financial composition.'),
  ]},
  {id:'contrast', name:'Performance Contrast', description:'Winner, loser, and mixed-market stories', variants:[
    variant('contrast-duel', 'A', 'Winner / loser duel', 'Separate branded result panels for contrasted assets.', contrastA, 'Stacked winner and loser panels, exact start/end callouts, dramatic contrast lighting and strong outcome headline.'),
    variant('contrast-intersecting', 'B', 'Intersecting comparison', 'Combined chart with exact winner and loser callouts.', contrastB, 'One protected combined chart, endpoint callouts, bold winner/loser headline and clean brand-owned framing.'),
    variant('contrast-scoreboard', 'C', 'Ranked scoreboard', 'A cinematic duel with ranked verified outcomes.', contrastC, 'Cinematic market duel, ranked outcome hierarchy, compact protected chart, dramatic but factual result storytelling.'),
  ]},
  {id:'separated', name:'Separated Performance', description:'Individual asset modules', variants:[
    variant('separated-grid', 'A', 'Responsive grid', 'A clean card for every selected asset.', cardsA, 'Individual verified asset cards arranged in a clear responsive grid with one brand-owned editorial headline.'),
    variant('separated-stacked', 'B', 'Stacked cards', 'Offset editorial cards connected into one story.', cardsB, 'Offset stacked cards with visual connections, exact mini charts and a calm premium background.'),
    variant('separated-orbiting', 'C', 'Orbiting cards', 'Dynamic modules orbiting the shared market story.', cardsC, 'Dynamic modular cards around a central market story, balanced spacing, exact per-asset values and lines.'),
  ]},
  {id:'combined', name:'Combined Performance', description:'One protected multi-series chart', variants:[
    variant('combined-rounded', 'A', 'Rounded chart', 'A generous arched chart with exact callouts.', combinedA, 'Large arched combined chart, horizon-like depth, exact callouts and refined futuristic financial atmosphere.'),
    variant('combined-minimal', 'B', 'Minimal chart', 'A quiet spotlight chart with premium restraint.', combinedB, 'Round spotlight chart, minimal typography, restrained light, clean legend and exceptional negative space.'),
    variant('combined-editorial', 'C', 'Editorial chart with callouts', 'Typography-forward chart with winner and loser callouts.', combinedC, 'Typography-forward editorial composition, protected multi-line chart, exact endpoint callouts and compact brand footer.'),
  ]},
]

export const TEMPLATE_VARIANTS = TEMPLATE_CATEGORIES.flatMap(category => category.variants.map(item => ({
  ...item,
  categoryId:category.id,
  categoryName:category.name,
  min:1,
  max:6,
})))

export function findTemplateVariant(id) {
  return TEMPLATE_VARIANTS.find(item => item.id === id)
}
