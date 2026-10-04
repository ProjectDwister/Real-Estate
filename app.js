const MANIFEST_URL='data/data_manifest.json';
const COVERAGE_URL='data/coverage.csv';
const STATUS_URL='data/status.json';
let rawData=[],filteredData=[],coverage=[],charts={};

const norm=v=>String(v??'').trim();
const num=v=>{const n=Number(String(v??'').replace(/[^0-9.-]/g,''));return Number.isFinite(n)?n:0};
const fmtNum=n=>Number.isFinite(Number(n))?new Intl.NumberFormat('en-IN').format(Number(n)):'—';
const fmtINR=n=>{n=Number(n);if(!Number.isFinite(n)||n===0)return'—';if(Math.abs(n)>=1e7)return'₹'+(n/1e7).toFixed(2)+' cr';if(Math.abs(n)>=1e5)return'₹'+(n/1e5).toFixed(2)+' lakh';return new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:0}).format(n)};
function median(vals){const a=vals.map(Number).filter(v=>Number.isFinite(v)&&v>0).sort((a,b)=>a-b);if(!a.length)return 0;const m=Math.floor(a.length/2);return a.length%2?a[m]:(a[m-1]+a[m])/2}
function parseDate(v,yearHint=''){const s=norm(v);let m=s.match(/^(\d{4})-(\d{2})-(\d{2})$/);if(m)return{year:m[1],month:m[2],day:m[3],ym:`${m[1]}-${m[2]}`,iso:s};m=s.match(/^(\d{1,2})[\/-](\d{1,2})[\/-](\d{4})$/);if(m)return{year:m[3],month:m[2].padStart(2,'0'),day:m[1].padStart(2,'0'),ym:`${m[3]}-${m[2].padStart(2,'0')}`,iso:`${m[3]}-${m[2].padStart(2,'0')}-${m[1].padStart(2,'0')}`};const y=norm(yearHint);return{year:y,month:'',day:'',ym:y?`${y}-??`:'',iso:s}}
function loadCsv(url){return new Promise((resolve,reject)=>Papa.parse(url,{download:true,header:true,skipEmptyLines:true,complete:r=>resolve(r.data),error:reject}))}
function sroNum(v){const m=norm(v).match(/(\d+)(?!.*\d)/);return m?m[1]:''}
function docIdentity(r){return `${norm(r.year)}|${norm(r.doc_no)}`}
function mergeRecords(base,enriched){
  const rows=base.map(r=>({...r,_sourcePriority:0}));
  for(const e0 of enriched){
    const e={...e0,_sourcePriority:1};
    const same=[];
    for(let i=0;i<rows.length;i++) if(docIdentity(rows[i])===docIdentity(e)) same.push(i);
    if(same.length===0){rows.push(e);continue}
    if(same.length===1){rows[same[0]]=e;continue}
    const ed=parseDate(e.registration_date,e.year).iso;
    const es=sroNum(e.sro_name);
    let idx=same.find(i=>parseDate(rows[i].registration_date,rows[i].year).iso===ed && (!es||!sroNum(rows[i].sro_name)||sroNum(rows[i].sro_name)===es));
    if(idx===undefined) idx=same.find(i=>parseDate(rows[i].registration_date,rows[i].year).iso===ed);
    if(idx===undefined) idx=same.find(i=>es&&sroNum(rows[i].sro_name)===es);
    if(idx===undefined){rows.push(e);continue}
    rows[idx]=e;
  }
  return rows;
}
async function boot(){
  try{
    const manifest=await fetch(MANIFEST_URL).then(r=>r.json());
    const baseUrls=manifest.base||['data/master_transactions.csv'];
    const enrichUrls=(manifest.enriched||[]).map(x=>typeof x==='string'?x:x.url);
    const [baseSets,enrichSets,c,s]=await Promise.all([
      Promise.all(baseUrls.map(loadCsv)),
      Promise.all(enrichUrls.map(loadCsv)),
      loadCsv(COVERAGE_URL),
      fetch(STATUS_URL).then(r=>r.ok?r.json():{}).catch(()=>({}))
    ]);
    const base=baseSets.flat(), enriched=enrichSets.flat();
    rawData=mergeRecords(base,enriched).map((r,i)=>({...r,_id:i,_date:parseDate(r.registration_date,r.year)}));
    rawData.sort((a,b)=>b._date.iso.localeCompare(a._date.iso)||norm(a.doc_no).localeCompare(norm(b.doc_no),'en-IN',{numeric:true}));
    coverage=c;
    renderStatus(s);
    initFilters();
    applyFilters();
    renderCoverage();
  }catch(e){
    console.error(e);
    document.getElementById('lastUpdated').textContent='Dataset unavailable';
    renderCoverage();
  }
}
function renderStatus(s){document.getElementById('lastUpdated').textContent=s.last_built_at||'Not yet built';document.getElementById('coverageSummary').textContent=s.summary||`${fmtNum(rawData.length)} records loaded`;document.getElementById('datasetQuality').textContent=s.quality_label||'Backfill in progress'}
function renderCoverage(){const el=document.getElementById('coverageGrid');if(!coverage.length){el.innerHTML='<p>No coverage file loaded.</p>';return}el.innerHTML=coverage.map(r=>`<div class="coverage-year ${norm(r.status).toLowerCase()}"><strong>${r.year}</strong><span>${norm(r.status)||'Pending'}</span><small>${num(r.records)?fmtNum(r.records):''}</small></div>`).join('')}
function unique(getter){return [...new Set(rawData.map(getter).map(norm).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'en-IN',{numeric:true}))}
function fill(id,vals){document.getElementById(id).innerHTML='<option value="all">All</option>'+vals.map(v=>`<option value="${v.replaceAll('"','&quot;')}">${v}</option>`).join('')}
function initFilters(){fill('yearFilter',unique(r=>r._date.year).sort((a,b)=>b-a));fill('villageFilter',unique(r=>r.village));fill('propertyFilter',unique(r=>r.property_no));fill('docGroupFilter',unique(r=>r.doc_group));fill('docTypeFilter',unique(r=>r.document_name));['yearFilter','villageFilter','propertyFilter','docGroupFilter','docTypeFilter','searchBox'].forEach(id=>document.getElementById(id).addEventListener('input',applyFilters));document.getElementById('downloadCsv').addEventListener('click',downloadCsv);document.getElementById('resetFilters').addEventListener('click',()=>{['yearFilter','villageFilter','propertyFilter','docGroupFilter','docTypeFilter'].forEach(id=>document.getElementById(id).value='all');document.getElementById('searchBox').value='';applyFilters()})}
function applyFilters(){const y=document.getElementById('yearFilter').value,v=document.getElementById('villageFilter').value,p=document.getElementById('propertyFilter').value,g=document.getElementById('docGroupFilter').value,d=document.getElementById('docTypeFilter').value,q=norm(document.getElementById('searchBox').value).toLowerCase();filteredData=rawData.filter(r=>(y==='all'||r._date.year===y)&&(v==='all'||norm(r.village)===v)&&(p==='all'||norm(r.property_no)===p)&&(g==='all'||norm(r.doc_group)===g)&&(d==='all'||norm(r.document_name)===d)&&(!q||[r.doc_no,r.property_description,r.building_name,r.unit_no,r.sro_name,r.segment,r.tag,r.wing,r.cts_cluster,r.notes].join(' ').toLowerCase().includes(q)));render()}
function render(){renderKpis();renderCharts();renderTable()}
function renderKpis(){const sales=filteredData.filter(r=>r.doc_group==='Sale / Agreement');const rents=filteredData.filter(r=>r.doc_group==='Rent / Licence');document.getElementById('kpiRecords').textContent=fmtNum(filteredData.length);document.getElementById('kpiSale').textContent=fmtNum(sales.length);document.getElementById('kpiRent').textContent=fmtNum(rents.length);const rate=median(sales.map(r=>num(r.rate_per_sqft)));document.getElementById('kpiRate').textContent=rate?'₹'+fmtNum(Math.round(rate))+' / sq ft':'—';document.getElementById('kpiRentAmount').textContent=fmtINR(median(rents.map(r=>num(r.rent_amount))));document.getElementById('kpiConsideration').textContent=fmtINR(median(sales.map(r=>num(r.consideration_amount))))}
function group(rows,fn){const m=new Map();rows.forEach(r=>{const k=fn(r)||'Unknown';m.set(k,(m.get(k)||0)+1)});return [...m.entries()]}
function destroy(k){if(charts[k])charts[k].destroy()}
function chart(id,type,labels,data,label){destroy(id);charts[id]=new Chart(document.getElementById(id),{type,data:{labels,datasets:[{label,data}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:type==='doughnut'}}}})}
function yearlyMedian(field,pred=()=>true){const years=[...new Set(filteredData.map(r=>r._date.year).filter(Boolean))].sort();return[years,years.map(y=>median(filteredData.filter(r=>r._date.year===y&&pred(r)).map(r=>num(r[field]))))]}
function renderCharts(){let a=group(filteredData,r=>r._date.year).filter(x=>x[0]!=='Unknown').sort((x,y)=>x[0]-y[0]);chart('annualChart','bar',a.map(x=>x[0]),a.map(x=>x[1]),'Registrations');let m=group(filteredData,r=>r._date.ym).filter(x=>!x[0].includes('??')).sort((x,y)=>x[0].localeCompare(y[0]));chart('monthlyChart','line',m.map(x=>x[0]),m.map(x=>x[1]),'Registrations');let mix=group(filteredData,r=>r.doc_group||r.document_name).sort((x,y)=>y[1]-x[1]);chart('docTypeChart','doughnut',mix.map(x=>x[0]),mix.map(x=>x[1]),'Records');let [yrs,rates]=yearlyMedian('rate_per_sqft',r=>r.doc_group==='Sale / Agreement');chart('rateChart','line',yrs,rates,'Median ₹/sq ft');let [ry,rv]=yearlyMedian('rent_amount',r=>r.doc_group==='Rent / Licence');chart('rentChart','line',ry,rv,'Median rent');let b=group(filteredData,r=>norm(r.building_name)||norm(r.property_description).slice(0,42)||'Unknown').sort((x,y)=>y[1]-x[1]).slice(0,12);chart('buildingChart','bar',b.map(x=>x[0]),b.map(x=>x[1]),'Registrations')}
function renderTable(){
  document.getElementById('tableCount').textContent=`${fmtNum(filteredData.length)} rows`;
  const body=document.querySelector('#recordsTable tbody');
  body.innerHTML=filteredData.slice(0,2000).map(r=>`<tr>
    <td>${r._date.year}</td><td>${norm(r.registration_date)}</td><td>${norm(r.execution_date)}</td><td>${norm(r.doc_no)}</td>
    <td>${norm(r.doc_group)}</td><td>${norm(r.document_name)}</td><td>${norm(r.category)}</td><td>${norm(r.village)}</td>
    <td>${norm(r.property_no)}</td><td>${norm(r.segment)}</td><td>${norm(r.building_name)}</td><td>${norm(r.wing)}</td>
    <td>${norm(r.unit_no)}</td><td>${norm(r.floor_no)}</td><td>${num(r.area_sqft)?fmtNum(Math.round(num(r.area_sqft))):'—'}</td>
    <td>${fmtINR(num(r.consideration_amount))}</td><td>${fmtINR(num(r.market_value))}</td><td>${num(r.rate_per_sqft)?'₹'+fmtNum(Math.round(num(r.rate_per_sqft))):'—'}</td>
    <td>${fmtINR(num(r.rent_amount))}</td><td>${fmtINR(num(r.deposit_amount))}</td><td>${norm(r.sro_name)}</td><td>${norm(r.record_quality)}</td>
  </tr>`).join('')||'<tr><td colspan="22">No records for this filter.</td></tr>'
}
function downloadCsv(){const clean=filteredData.map(({_id,_date,_sourcePriority,...r})=>r);const blob=new Blob([Papa.unparse(clean)],{type:'text/csv;charset=utf-8;'});const u=URL.createObjectURL(blob);const a=document.createElement('a');a.href=u;a.download='mumbai_real_estate_filtered.csv';a.click();URL.revokeObjectURL(u)}
boot();