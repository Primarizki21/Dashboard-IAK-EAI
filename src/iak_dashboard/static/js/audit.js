/**
 * Modul Audit Trail Data-Level EAI (Lineage & Riwayat Ekstraksi ETL)
 */

async function loadAuditLog() {
  try {
    const res = await fetch('/api/mining/audit');
    if (!res.ok) throw new Error('Gagal memuat log audit');
    const data = await res.json();

    const tbody = document.getElementById('auditTableBody');
    if (!tbody) return;

    tbody.innerHTML = '';
    data.audit_log.forEach(row => {
      const tr = document.createElement('tr');
      tr.className = 'hover:bg-slate-50';
      tr.innerHTML = `
        <td class="py-2 px-2 text-slate-400 font-mono">${row.id}</td>
        <td class="py-2 px-3 font-medium text-slate-800">${row.source_name}</td>
        <td class="py-2 px-2 font-mono"><span class="px-1.5 py-0.5 rounded bg-slate-100 text-slate-700">${row.source_format}</span></td>
        <td class="py-2 px-3 font-mono text-slate-600">${row.target_table}</td>
        <td class="py-2 px-2 text-right">${row.records_extracted.toLocaleString()}</td>
        <td class="py-2 px-2 text-right">${row.records_loaded.toLocaleString()}</td>
        <td class="py-2 px-2 text-center"><span class="px-2 py-0.5 rounded text-xs bg-emerald-100 text-emerald-800 font-medium">${row.status}</span></td>
        <td class="py-2 px-3 text-slate-500 font-mono">${row.executed_at}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) {
    console.error('Error memuat audit log:', e);
  }
}
