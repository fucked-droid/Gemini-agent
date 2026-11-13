const assert = require('assert');
const { add, subtract, multiply, divide } = require('./calculator');

console.log('Running calculator tests...');

// Test add
assert.strictEqual(add(2, 3), 5, 'add(2, 3) should equal 5');
assert.strictEqual(add(-1, 1), 0, 'add(-1, 1) should equal 0');
console.log('✓ add tests passed');

// Test subtract
assert.strictEqual(subtract(5, 3), 2, 'subtract(5, 3) should equal 2');
assert.strictEqual(subtract(3, 5), -2, 'subtract(3, 5) should equal -2');
console.log('✓ subtract tests passed');

// Test multiply
assert.strictEqual(multiply(4, 3), 12, 'multiply(4, 3) should equal 12');
assert.strictEqual(multiply(-2, 3), -6, 'multiply(-2, 3) should equal -6');
console.log('✓ multiply tests passed');

// Test divide
assert.strictEqual(divide(10, 2), 5, 'divide(10, 2) should equal 5');
assert.strictEqual(divide(5, 2), 2.5, 'divide(5, 2) should equal 2.5');

// Test division by zero
let errorThrown = false;
try {
  divide(5, 0);
} catch (e) {
  errorThrown = true;
  assert.strictEqual(e.message, 'Division by zero is not allowed.');
}
assert.strictEqual(errorThrown, true, 'divide(5, 0) should throw an error');
console.log('✓ divide tests passed');

console.log('All calculator tests passed successfully!');
