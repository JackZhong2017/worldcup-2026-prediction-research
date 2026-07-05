const modules = ['Match Explorer', 'Calibration', 'Market Quality', 'Pattern Discovery'];

export default function Home() {
  return <main>
    <p className="eyebrow">RESEARCH WORKBENCH / V2</p>
    <h1>Football markets,<br />measured over time.</h1>
    <p className="lede">A reproducible laboratory for calibration, uncertainty, and prediction-market structure.</p>
    <section>{modules.map((name, index) => <article key={name}><span>0{index + 1}</span><h2>{name}</h2><p>Dataset pending</p></article>)}</section>
    <footer>Research only · No betting recommendations</footer>
  </main>;
}
