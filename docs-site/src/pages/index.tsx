import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';

export default function Home() {
  return (
    <Layout title="ARIA Docs" description="ARIA documentation — Developers & User Guide">
      <main style={{maxWidth: 860, margin: '0 auto', padding: '4rem 1.5rem'}}>
        <h1 style={{fontSize: '2.5rem', marginBottom: '0.5rem'}}>ARIA Documentation</h1>
        <p style={{fontSize: '1.15rem', color: 'var(--ifm-color-emphasis-700)'}}>
          Ask. Reason. Illuminate. Act. — natural-language analytics on your own data.
        </p>
        <div style={{display: 'flex', gap: '1rem', marginTop: '2rem', flexWrap: 'wrap'}}>
          <Link className="button button--primary button--lg" to="/guide/intro">User Guide (Academy)</Link>
          <Link className="button button--secondary button--lg" to="/developers/intro">Developer Docs</Link>
          <Link className="button button--outline button--lg" href="pathname:///api.html">API Reference</Link>
        </div>
      </main>
    </Layout>
  );
}
