'use client';

export default function Learn() {
  return (
    <div style={{ minHeight: '100vh', fontFamily: "var(--font-sans), sans-serif" }}>
      {/* Hero */}
      <section style={{ textAlign: 'center', padding: '88px 56px 60px' }}>
        <h1 style={{ fontSize: '64px', fontWeight: 600, marginBottom: '24px' }}>
          How to Interpret Results
        </h1>
        <p style={{ fontSize: '18px', color: 'var(--text-secondary)', maxWidth: '700px', margin: '0 auto', lineHeight: 1.7 }}>
          Western blots can look intimidating, but once you understand the basics, they tell a clear story. Here's what to look for.
        </p>
      </section>

      {/* Western Blot Basics */}
      <section style={{ padding: '80px 56px', borderTop: '1px solid var(--border)', maxWidth: '1000px', margin: '0 auto' }}>
        <h2 style={{ fontSize: '42px', fontWeight: 600, marginBottom: '32px' }}>What is a Western Blot?</h2>
        <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8, marginBottom: '24px' }}>
          A western blot is a molecular biology technique used to detect and quantify specific proteins in a sample. The process works like this:
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '40px', marginTop: '32px' }}>
          <div style={{ backgroundColor: 'var(--accent-faint)', padding: '24px', borderRadius: '8px', border: '1px solid rgba(74,214,176,.2)' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '12px', color: 'var(--accent)' }}>
              1. Extraction & Loading
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: 1.6 }}>
              Proteins are extracted from cells or tissues and loaded onto a gel. Equal amounts are typically used to make comparisons fair.
            </p>
          </div>
          <div style={{ backgroundColor: 'var(--accent-faint)', padding: '24px', borderRadius: '8px', border: '1px solid rgba(74,214,176,.2)' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '12px', color: 'var(--accent)' }}>
              2. Gel Electrophoresis
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: 1.6 }}>
              An electric field separates proteins by size. Smaller proteins move faster; larger ones move slower.
            </p>
          </div>
          <div style={{ backgroundColor: 'var(--accent-faint)', padding: '24px', borderRadius: '8px', border: '1px solid rgba(74,214,176,.2)' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '12px', color: 'var(--accent)' }}>
              3. Transfer to Membrane
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: 1.6 }}>
              Proteins are transferred from the gel onto a nitrocellulose or PVDF membrane for detection.
            </p>
          </div>
          <div style={{ backgroundColor: 'var(--accent-faint)', padding: '24px', borderRadius: '8px', border: '1px solid rgba(74,214,176,.2)' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '12px', color: 'var(--accent)' }}>
              4. Antibody Detection
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: 1.6 }}>
              Specific antibodies bind to your target protein and are visualized using chemiluminescence or fluorescence.
            </p>
          </div>
        </div>
      </section>

      {/* Reading Results */}
      <section style={{ padding: '80px 56px', borderTop: '1px solid var(--border)', maxWidth: '1000px', margin: '0 auto' }}>
        <h2 style={{ fontSize: '42px', fontWeight: 600, marginBottom: '32px' }}>Reading Your Results</h2>
        
        <div style={{ marginBottom: '40px' }}>
          <h3 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '16px', color: 'var(--warning)' }}>Band Intensity</h3>
          <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
            The darker or brighter a band, the more of that protein is present. A faint band means low protein levels; a dark band means high levels. This is what you're really measuring.
          </p>
        </div>

        <div style={{ marginBottom: '40px' }}>
          <h3 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '16px', color: 'var(--warning)' }}>Protein Size (Molecular Weight)</h3>
          <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
            Where a band appears on the blot tells you the molecular weight of the protein. Your target protein should appear at a specific size. If it appears at a different size, it might be a degradation product or splice variant.
          </p>
        </div>

        <div style={{ marginBottom: '40px' }}>
          <h3 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '16px', color: 'var(--warning)' }}>Loading Controls</h3>
          <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
            A loading control like GAPDH, beta-actin, or tubulin appears at the bottom of most western blots. This shows that equal amounts of protein were loaded in each lane. If loading controls differ significantly between lanes, any comparison becomes questionable.
          </p>
        </div>

        <div>
          <h3 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '16px', color: 'var(--warning)' }}>Multiple Lanes</h3>
          <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
            Each lane represents a different condition or treatment. You compare band intensity across lanes to see if your protein levels changed in response to treatment.
          </p>
        </div>
      </section>

      {/* Common Results */}
      <section style={{ padding: '80px 56px', borderTop: '1px solid var(--border)', maxWidth: '1000px', margin: '0 auto' }}>
        <h2 style={{ fontSize: '42px', fontWeight: 600, marginBottom: '32px' }}>Result Interpretations in HiveBlot</h2>
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '32px', marginTop: '32px' }}>
          <div style={{ padding: '20px', backgroundColor: 'var(--accent-soft)', borderRadius: '8px', borderLeft: '4px solid var(--accent)' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '8px', color: 'var(--accent)' }}>Detected</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
              The protein is present in the cell line or tissue. A band is visible and clear.
            </p>
          </div>

          <div style={{ padding: '20px', backgroundColor: 'var(--warning-soft)', borderRadius: '8px', borderLeft: '4px solid var(--warning)' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '8px', color: 'var(--warning)' }}>Upregulated</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
              The protein is more abundant than in a control or compared condition. The band is darker/brighter.
            </p>
          </div>

          <div style={{ padding: '20px', backgroundColor: 'var(--error-soft)', borderRadius: '8px', borderLeft: '4px solid var(--error)' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '8px', color: 'var(--error)' }}>Downregulated</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
              The protein is less abundant than in a control or compared condition. The band is fainter.
            </p>
          </div>

          <div style={{ padding: '20px', backgroundColor: 'var(--blue-soft)', borderRadius: '8px', borderLeft: '4px solid var(--blue)' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '8px', color: 'var(--blue)' }}>Not Detected</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
              The protein is absent or below the detection limit. No band is visible.
            </p>
          </div>
        </div>
      </section>

      {/* Tips */}
      <section style={{ padding: '80px 56px', borderTop: '1px solid var(--border)', maxWidth: '1000px', margin: '0 auto' }}>
        <h2 style={{ fontSize: '42px', fontWeight: 600, marginBottom: '32px' }}>Tips for Interpreting Results</h2>
        
        <ul style={{ color: 'var(--text-secondary)', lineHeight: 2, fontSize: '16px', paddingLeft: '20px' }}>
          <li><strong style={{ color: 'var(--text-primary)' }}>Always check the loading control.</strong> Unequal loading makes protein comparisons invalid.</li>
          <li><strong style={{ color: 'var(--text-primary)' }}>Look for the expected size.</strong> An unexpected band size suggests degradation, modification, or off-target antibody binding.</li>
          <li><strong style={{ color: 'var(--text-primary)' }}>Use biological replicates.</strong> A single lane doesn't prove much. Multiple replicates increase confidence.</li>
          <li><strong style={{ color: 'var(--text-primary)' }}>Check the antibody specificity.</strong> The antibody used matters. Different antibodies can give different results.</li>
          <li><strong style={{ color: 'var(--text-primary)' }}>Consider the context.</strong> Cell type, condition, and species all affect what you see.</li>
        </ul>
      </section>
    </div>
  );
}
