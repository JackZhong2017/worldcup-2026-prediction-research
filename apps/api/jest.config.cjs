/** @type {import('jest').Config} */
module.exports = {
  rootDir: '.',
  testEnvironment: 'node',
  testMatch: ['<rootDir>/src/**/*.spec.ts'],
  transform: {
    '^.+\\.ts$': ['ts-jest', { tsconfig: '<rootDir>/tsconfig.json' }],
  },
  moduleNameMapper: {
    '^@sprp/database$': '<rootDir>/../../packages/database/src/index.ts',
    '^(\\.{1,2}/.*)\\.js$': '$1',
  },
};
