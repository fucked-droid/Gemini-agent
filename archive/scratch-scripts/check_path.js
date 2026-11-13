const path = require('path');
const workspace = path.resolve(process.cwd());
const target = path.resolve('C:\\Windows\\win.ini');
const relative = path.relative(workspace, target);
console.log({
  workspace,
  target,
  relative,
  blocked: relative.startsWith('..') || path.isAbsolute(relative)
});
