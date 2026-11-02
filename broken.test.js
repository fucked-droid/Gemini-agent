const assert = require('assert');
const { greet } = require('./broken');

console.log('Running broken.js tests...');

assert.strictEqual(greet(), 'Hello World', 'greet() should return "Hello World"');

console.log('✓ All broken.js tests passed successfully!');
