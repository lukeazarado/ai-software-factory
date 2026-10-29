/** Gera CSS local para a Agenda do Atleta. Execução de desenvolvimento somente. */
const fs = require('node:fs');
const path = require('node:path');
const { compile } = require('tailwindcss');
const web = path.join(__dirname, 'web');
const tw = path.dirname(require.resolve('tailwindcss/package.json'));
const source = fs.readFileSync(path.join(web, 'index.html'), 'utf8') + '\n' + fs.readFileSync(path.join(web, 'app.js'), 'utf8');
const classes = new Set();
for (const match of source.matchAll(/class=["']([^"']+)["']/g)) {
  for (const cls of match[1].split(/\s+/)) if (cls && !cls.includes('${') && !cls.includes('}') && !cls.includes('\\')) classes.add(cls);
}
for (const match of source.matchAll(/cls:['"]([^'"]+)['"]/g)) {
  for (const cls of match[1].split(/\s+/)) classes.add(cls);
}
for (const match of source.matchAll(/classList\.(?:add|remove|toggle)\(['"]([^'"\s]+)['"]/g)) classes.add(match[1]);
for (const cls of ['bg-indigo-50', 'text-indigo-600', 'bg-emerald-50', 'bg-amber-50']) classes.add(cls);
const css = fs.readFileSync(path.join(tw, 'theme.css'), 'utf8') + '\n' + fs.readFileSync(path.join(tw, 'preflight.css'), 'utf8') + '\n@tailwind utilities;';
compile(css).then(result => {
  const generated = result.build([...classes]);
  fs.writeFileSync(path.join(web, 'app.css'), generated + '\n' + fs.readFileSync(path.join(web, 'custom.css'), 'utf8'));
  console.log(`CSS gerado (${classes.size} classes usadas) em web/app.css`);
}).catch(error => { console.error(error); process.exitCode = 1; });