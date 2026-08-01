import phoneDark from '../../assets/analytics-templates/phone-market-reference.png'
import phoneLight from '../../assets/analytics-templates/phone-comparison.png'
import laptopCinematic from '../../assets/analytics-templates/desktop-dashboard-reference.png'
import laptopWide from '../../assets/analytics-templates/desktop-dashboard.png'
import growthImage from '../../assets/analytics-templates/growth-spotlight.png'
import contrastImage from '../../assets/analytics-templates/winner-loser.png'
import separatedImage from '../../assets/analytics-templates/separated-performance-reference.jpg'
import combinedImage from '../../assets/analytics-templates/combined-performance-reference.jpg'

export const TEMPLATE_CATEGORIES = [
  {id:'phone', name:'Phone Market View', description:'Mobile market presentation', variants:[
    {id:'phone-centered', name:'Centered phone', description:'A centered premium phone with complete market view.', image:phoneDark},
    {id:'phone-split-stat', name:'Split-stat phone', description:'Phone chart with exact result callouts on both sides.', image:phoneLight},
    {id:'phone-editorial', name:'Compact editorial phone', description:'A tighter editorial phone composition for fast reading.', image:phoneDark},
  ]},
  {id:'laptop', name:'Laptop Dashboard', description:'Desktop market presentation', variants:[
    {id:'laptop-cinematic', name:'Cinematic laptop', description:'Premium laptop with a dramatic chart-focused stage.', image:laptopCinematic},
    {id:'laptop-editorial', name:'Editorial laptop', description:'Headline-led laptop composition with calm spacing.', image:laptopWide},
    {id:'laptop-wide', name:'Wide dashboard laptop', description:'A wider multi-series dashboard presentation.', image:laptopCinematic},
  ]},
  {id:'growth', name:'Growth Spotlight', description:'Focused performance story', variants:[
    {id:'growth-card', name:'Performance card', description:'Exact movement presented in one protected result card.', image:growthImage},
    {id:'growth-hero', name:'Growth hero', description:'Large chart-led hero with brand-owned color and hierarchy.', image:growthImage},
    {id:'growth-milestone', name:'Milestone result', description:'Start, end, and movement framed as a verified milestone.', image:growthImage},
  ]},
  {id:'contrast', name:'Performance Contrast', description:'Winner, loser, and mixed-market stories', variants:[
    {id:'contrast-duel', name:'Winner / loser duel', description:'Two or more results contrasted with exact movements.', image:contrastImage},
    {id:'contrast-intersecting', name:'Intersecting comparison', description:'Combined lines and callouts inside a premium contrast field.', image:combinedImage},
    {id:'contrast-scoreboard', name:'Ranked scoreboard', description:'All selected assets ordered by verified performance.', image:contrastImage},
  ]},
  {id:'separated', name:'Separated Performance', description:'Individual asset modules', variants:[
    {id:'separated-grid', name:'Responsive grid', description:'One exact performance card for every selected asset.', image:separatedImage},
    {id:'separated-stacked', name:'Stacked cards', description:'Editorial stacked cards with clear movement hierarchy.', image:separatedImage},
    {id:'separated-orbiting', name:'Orbiting cards', description:'Dynamic modular cards orbiting the shared story.', image:separatedImage},
  ]},
  {id:'combined', name:'Combined Performance', description:'One protected multi-series chart', variants:[
    {id:'combined-rounded', name:'Rounded chart', description:'A generous rounded chart with exact data callouts.', image:combinedImage},
    {id:'combined-minimal', name:'Minimal chart', description:'Quiet, typography-first combined market story.', image:combinedImage},
    {id:'combined-editorial', name:'Editorial chart with callouts', description:'Combined verified chart with winner and loser callouts.', image:combinedImage},
  ]},
]

export const TEMPLATE_VARIANTS = TEMPLATE_CATEGORIES.flatMap(category => category.variants.map(variant => ({
  ...variant,
  categoryId:category.id,
  categoryName:category.name,
  min:1,
  max:6,
})))

export function findTemplateVariant(id) {
  return TEMPLATE_VARIANTS.find(item => item.id === id)
}
