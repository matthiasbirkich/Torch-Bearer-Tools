/** Targeted correction for ZoidTechnology Torch-Bearer-Tools Patch 0.4.
 * Removes the unsupported IR module for Y21B7W10034CCPD.
 * Does not recalculate manufacturer metrics or change serial spectral decoding.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';

export const MODEL = 'Y21B7W10034CCPD';
export const VERSION = '1.0.0';
const BEFORE = ['SPEC_V2', 'BL', 'IR', 'PPFD', 'TM30'];
const AFTER = BEFORE.filter(x => x !== 'IR');
const MARK = `Y2-IRfix:${VERSION}`;
const REL = 'assets/apps/__UNI__AC0AA31/www/app-service.js';

/** Accept only the exact original patched model layout, or our own result. */
export function correctModel(source) {
  const re = /\{\s*model\s*:\s*(['"])Y21B7W10034CCPD\1\s*,\s*modules\s*:\s*\[([^\]]*)\]\s*\}/g;
  const matches = [...source.matchAll(re)];
  if (matches.length !== 1) throw new Error(`Erwartet genau einen Eintrag fuer ${MODEL}, gefunden: ${matches.length}`);
  const entry = matches[0];
  const tokens = [...entry[2].matchAll(/(['"])([A-Z0-9_]+)\1/g)].map(m=>m[2]);
  const residue = entry[2].replace(/(['"])([A-Z0-9_]+)\1/g,'').replace(/[\s,]/g,'');
  if (residue) throw new Error('Unbekannte Modulsyntax. Keine automatische Aenderung.');
  if (JSON.stringify(tokens) === JSON.stringify(AFTER)) return {text:source, changed:false};
  if (JSON.stringify(tokens) !== JSON.stringify(BEFORE)) throw new Error(`Unerwartete Module: ${tokens.join(', ')}. Benoetigt wird Zoid Patch 0.4.`);
  const fixedEntry = entry[0].replace(/(['"])IR\1\s*,\s*/, '');
  return {text: source.slice(0,entry.index)+fixedEntry+source.slice(entry.index+entry[0].length), changed:true};
}

export function correctPatches(text) {
  const patches = JSON.parse(text);
  if (!Array.isArray(patches)) throw new Error('patches.json hat ein unbekanntes Format.');
  let targetCount=0, changed=false, markerCount=0;
  for (const file of patches) {
    if (file.path !== REL || !Array.isArray(file.data)) continue;
    for (const hunk of file.data) {
      if (!Array.isArray(hunk.lines)) throw new Error('Unbekanntes Hunkformat.');
      for (let i=0;i<hunk.lines.length;i++) {
        const line=hunk.lines[i];
        // Keep original/context lines and hunk line counts unchanged.
        if (!line.startsWith('+')) continue;
        if (line.includes(MODEL)) {
          targetCount++;
          const fix=correctModel(line.slice(1));
          hunk.lines[i]='+'+fix.text; changed ||= fix.changed;
        }
        if (hunk.lines[i].includes('Patch:0.4')) {
          markerCount++;
          if (!hunk.lines[i].includes(MARK)) {
            hunk.lines[i]=hunk.lines[i].replace('Patch:0.4',`Patch:0.4 ${MARK}`); changed=true;
          }
        }
      }
    }
  }
  if (targetCount!==1 || markerCount!==1) throw new Error('Die Patchdatei passt nicht eindeutig zu Zoid Patch 0.4. Nichts geaendert.');
  return {text:changed?JSON.stringify(patches,null,'\t')+'\n':text, changed};
}

export function correctCachedSource(text) {
  const fixed=correctModel(text);
  // Marker is informational; require a patched source before editing it.
  if (!text.includes('Patch:0.4')) throw new Error('Im vorhandenen data/patched fehlt die Kennung Patch:0.4.');
  if (!fixed.text.includes(MARK)) {
    fixed.text=fixed.text.replace('Patch:0.4',`Patch:0.4 ${MARK}`); fixed.changed=true;
  }
  return fixed;
}

function sha(bytes) {return createHash('sha256').update(bytes).digest('hex');}
export function prepare(root, dryRun=false) {
  root=path.resolve(root);
  const packagePath=path.join(root,'package.json');
  const indexPath=path.join(root,'source','index.js');
  if (!fs.existsSync(packagePath)||!fs.existsSync(indexPath)) throw new Error('Bitte die Dateien in app-patcher neben package.json kopieren.');
  const pkg=JSON.parse(fs.readFileSync(packagePath,'utf8'));
  if (pkg.scripts?.assemble!=='node source assemble') throw new Error('Unbekanntes assemble-Skript. Bitte den unveraenderten Zoid-Patcher verwenden.');
  const patchPath=path.join(root,'patches.json');
  const patchBytes=fs.readFileSync(patchPath);
  const patchFix=correctPatches(patchBytes.toString('utf8'));
  const plan=[{file:patchPath, bytes:patchBytes, ...patchFix}];
  const data=path.join(root,'data');
  if (fs.existsSync(data)) {
    const cached=path.join(data,'patched',REL);
    if (!fs.existsSync(cached)||!fs.existsSync(path.join(data,'keystore.jks'))) throw new Error('data ist unvollstaendig: gepatchte Quelle oder keystore.jks fehlt. data nicht loeschen; bitte Fehlermeldung melden.');
    const bytes=fs.readFileSync(cached);
    plan.push({file:cached,bytes,...correctCachedSource(bytes.toString('utf8'))});
    const manifest=path.join(path.dirname(cached),'manifest.json');
    if (fs.existsSync(manifest)) {
      const version=JSON.parse(fs.readFileSync(manifest,'utf8')).version?.name;
      if (!/^1\.6\.4(?:\D|\d|$)/.test(String(version))) throw new Error(`Vorhandene App-Version ${version}: dieses Paket ist fuer Flameeye 1.6.4 vorgesehen.`);
      console.log('App-Version laut manifest.json:',version);
    }
  } else if (!fs.existsSync(path.join(root,'flameeye.apk'))) {
    throw new Error('Ohne vorhandenen data-Ordner wird die originale Flameeye 1.6.4 als flameeye.apk benoetigt.');
  }
  console.log('Modell:',MODEL);
  console.log('Neue Module:',AFTER.join(', '));
  if (dryRun) {console.log('Nur geprueft. Keine Dateien geaendert.');return {changed:plan.some(p=>p.changed),backup:null};}
  const changes=plan.filter(p=>p.changed);
  if (!changes.length) {console.log('Korrektur bereits vorhanden. APK darf erneut gebaut werden.');return {changed:false,backup:null};}
  const stamp=new Date().toISOString().replace(/[:.]/g,'-');
  const backup=path.join(root,`y2-irfix-backup-${stamp}`);
  fs.mkdirSync(backup);
  // Backup everything to be changed before the first modification.
  const report={fix:VERSION,model:MODEL,created_utc:new Date().toISOString(),files:[]};
  for (const item of changes) {
    const rel=path.relative(root,item.file), dest=path.join(backup,rel);
    fs.mkdirSync(path.dirname(dest),{recursive:true}); fs.writeFileSync(dest,item.bytes);
    report.files.push({path:rel,before_sha256:sha(item.bytes),after_sha256:sha(item.text)});
  }
  const oldApk=path.join(data,'flameeye-signed.apk');
  if (fs.existsSync(oldApk)) fs.copyFileSync(oldApk,path.join(backup,'flameeye-signed-before-irfix.apk'));
  fs.writeFileSync(path.join(backup,'backup.json'),JSON.stringify(report,null,2)+'\n');
  const written=[];
  try {
    for (const item of changes) {
      // Refuse overwriting a concurrent modification.
      if (!fs.readFileSync(item.file).equals(item.bytes)) throw new Error('Datei wurde inzwischen anderweitig geaendert: '+item.file);
      fs.writeFileSync(item.file,item.text,'utf8');written.push(item);
    }
  } catch (error) {
    for (const item of written.reverse()) fs.writeFileSync(item.file,item.bytes);
    throw error;
  }
  console.log('Sicherung:',backup);
  console.log('Quellen korrigiert. Jetzt npm run assemble ausfuehren.');
  return {changed:true,backup};
}

const isMain=process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url);
if (isMain) {
  try {
    if (Number(process.versions.node.split('.')[0])<22) throw new Error('Node.js 22 oder neuer wird benoetigt.');
    const args=process.argv.slice(2);const dry=args.includes('--check');
    const root=args.find(a=>!a.startsWith('--'))||path.dirname(fileURLToPath(import.meta.url));
    prepare(root,dry);
  } catch(error) {console.error('ABBRUCH:',error.message);process.exitCode=1;}
}
