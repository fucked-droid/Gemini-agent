const assert = require('assert');
const { add } = require('./repair-demo');

console.log('Running repair-demo tests...');

assert.strictEqual(add(2, 3), 5, 'add(2, 3) should equal 5');
assert.strictEqual(add(-2, 5), 3, 'add(-2, 5) should equal 3');

console.log('✓ All repair-demo tests passed successfully!');
