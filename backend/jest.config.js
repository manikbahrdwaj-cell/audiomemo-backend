module.exports = {
    displayName: "Backend Unit Tests",
    testEnvironment: "node",
    
    // Test patterns
    testMatch: [
        "**/__tests__/**/*.test.js",
        "**/*.test.js"
    ],
    
    // Coverage configuration
    collectCoverageFrom: [
        "*.js",
        "!**/node_modules/**",
        "!**/dist/**",
        "!**/*.test.js",
        "!test_*.js"
    ],
    
    coverageThreshold: {
        global: {
            branches: 70,
            functions: 80,
            lines: 80,
            statements: 80
        }
    },
    
    // Reporters
    testReporters: ["default", "verbose"],
    
    // Timeout
    testTimeout: 10000,
    
    // Setup files
    setupFilesAfterEnv: [],
    
    // Module name mapper for mocking
    moduleNameMapper: {},
    
    // Transform files if needed
    transform: {},
    
    // Verbose output
    verbose: true,
    
    // Coverage reporters
    coverageReporters: [
        "text",
        "text-summary",
        "html",
        "json"
    ]
};
