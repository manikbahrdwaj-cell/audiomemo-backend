/**
 * Test Utilities and Fixtures for JavaScript Unit Tests (Phase 4, Step 4.1)
 * Provides reusable test helpers, mocks, and fixtures for all JavaScript unit tests
 */

/**
 * Generate valid 192-dimensional embeddings for testing
 */
const EmbeddingFixtures = {
    /**
     * Generate random 192-dimensional embedding in range [-1, 1]
     */
    validEmbedding192d() {
        return Array(192).fill(0).map(() => Math.random() * 2 - 1);
    },

    /**
     * Generate all-zeros embedding
     */
    zeroEmbedding192d() {
        return Array(192).fill(0);
    },

    /**
     * Generate all-ones embedding
     */
    onesEmbedding192d() {
        return Array(192).fill(1);
    },

    /**
     * Generate normalized unit vector embedding
     */
    unitVectorEmbedding() {
        const embedding = Array(192).fill(0).map(() => Math.random());
        const norm = Math.sqrt(
            embedding.reduce((sum, val) => sum + val * val, 0)
        );
        return embedding.map(val => val / norm);
    },

    /**
     * Generate embedding with NaN values
     */
    embeddingWithNaN() {
        const embedding = Array(192).fill(0).map(() => Math.random());
        embedding[50] = NaN;
        return embedding;
    },

    /**
     * Generate embedding with Infinity values
     */
    embeddingWithInfinity() {
        const embedding = Array(192).fill(0).map(() => Math.random());
        embedding[75] = Infinity;
        return embedding;
    },

    /**
     * Generate embedding with negative Infinity
     */
    embeddingWithNegativeInfinity() {
        const embedding = Array(192).fill(0).map(() => Math.random());
        embedding[100] = -Infinity;
        return embedding;
    },

    /**
     * Generate pair of similar embeddings
     */
    similarEmbeddingsPair(similarityLevel = 0.95) {
        const base = Array(192).fill(0).map(() => Math.random());
        const noise = Array(192).fill(0).map(() => Math.random() * (1 - similarityLevel));
        const second = base.map((val, i) => val + noise[i]);
        return [base, second];
    },

    /**
     * Generate batch of embeddings
     */
    batchEmbeddings(count = 100) {
        return Array(count).fill(0).map(() => this.validEmbedding192d());
    },

    /**
     * Generate identical embeddings for match testing
     */
    identicalEmbeddingsPair() {
        const embedding = this.validEmbedding192d();
        return [embedding, [...embedding]];
    },

    /**
     * Generate orthogonal embeddings
     */
    orthogonalEmbeddingsPair() {
        const embedding1 = Array(96).fill(1).concat(Array(96).fill(0));
        const embedding2 = Array(96).fill(0).concat(Array(96).fill(1));
        return [embedding1, embedding2];
    },

    /**
     * Generate opposite embeddings
     */
    oppositeEmbeddingsPair() {
        const embedding1 = Array(192).fill(1);
        const embedding2 = Array(192).fill(-1);
        return [embedding1, embedding2];
    },

    /**
     * Generate wrong dimension embedding
     */
    wrongDimensionEmbedding(dimension = 96) {
        return Array(dimension).fill(0.5);
    }
};

/**
 * Mock objects for testing
 */
const Mocks = {
    /**
     * Create mock logger for testing
     */
    createMockLogger() {
        return {
            info: jest.fn(),
            error: jest.fn(),
            warn: jest.fn(),
            debug: jest.fn(),
            log: jest.fn()
        };
    },

    /**
     * Create mock MongoDB collection
     */
    createMockCollection() {
        const data = {};
        return {
            insertOne: jest.fn((doc) => {
                data[doc._id] = doc;
                return Promise.resolve({ insertedId: doc._id });
            }),
            findOne: jest.fn((query) => {
                return Promise.resolve(null);
            }),
            updateOne: jest.fn((filter, update) => {
                return Promise.resolve({ modifiedCount: 1 });
            }),
            deleteOne: jest.fn((query) => {
                return Promise.resolve({ deletedCount: 1 });
            }),
            find: jest.fn(() => ({
                toArray: jest.fn(() => Promise.resolve([]))
            })),
            _data: data
        };
    },

    /**
     * Create mock Express app
     */
    createMockExpressApp() {
        return {
            get: jest.fn(),
            post: jest.fn(),
            put: jest.fn(),
            delete: jest.fn(),
            use: jest.fn(),
            listen: jest.fn((port, callback) => {
                if (callback) callback();
            })
        };
    },

    /**
     * Create mock WebSocket
     */
    createMockWebSocket() {
        return {
            on: jest.fn(),
            emit: jest.fn(),
            send: jest.fn(),
            close: jest.fn(),
            addEventListener: jest.fn(),
            removeEventListener: jest.fn(),
            readyState: 1,
            OPEN: 1,
            CLOSED: 3
        };
    }
};

/**
 * Test data generators
 */
const TestData = {
    /**
     * Generate similarity test cases
     */
    similarityTestCases() {
        return [
            {
                name: 'identical_vectors',
                embedding1: Array(192).fill(0.5),
                embedding2: Array(192).fill(0.5),
                expectedRange: [0.95, 1.0]
            },
            {
                name: 'orthogonal_vectors',
                embedding1: Array(96).fill(1).concat(Array(96).fill(0)),
                embedding2: Array(96).fill(0).concat(Array(96).fill(1)),
                expectedRange: [0.3, 0.7]
            },
            {
                name: 'zero_similarity',
                embedding1: Array(96).fill(1).concat(Array(96).fill(0)),
                embedding2: Array(96).fill(0).concat(Array(96).fill(1)),
                expectedRange: [0, 0.5]
            }
        ];
    },

    /**
     * Generate batch comparison test data
     */
    batchComparisonTestData() {
        const baseEmbedding = EmbeddingFixtures.validEmbedding192d();
        return {
            enrolled: [
                baseEmbedding,
                baseEmbedding.map(x => x + 0.01),
                baseEmbedding.map(x => x + 0.02)
            ],
            verification: baseEmbedding,
            expectedMatches: 1
        };
    },

    /**
     * Generate threshold test cases
     */
    thresholdTestCases() {
        return [
            { value: 0.5, isValid: true },
            { value: 0.75, isValid: true },
            { value: 1.0, isValid: true },
            { value: 0.3, isValid: false },
            { value: 1.1, isValid: false }
        ];
    }
};

/**
 * Test utilities and helpers
 */
const TestUtils = {
    /**
     * Wait for async operation
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    },

    /**
     * Generate random value in range
     */
    randomInRange(min, max) {
        return Math.random() * (max - min) + min;
    },

    /**
     * Check if value is within range
     */
    isInRange(value, min, max) {
        return value >= min && value <= max;
    },

    /**
     * Compare floating point numbers
     */
    approxEqual(a, b, tolerance = 0.0001) {
        return Math.abs(a - b) < tolerance;
    },

    /**
     * Create test suite context
     */
    createTestContext() {
        return {
            startTime: Date.now(),
            metrics: {},
            recordMetric(name, value) {
                if (!this.metrics[name]) {
                    this.metrics[name] = [];
                }
                this.metrics[name].push(value);
            },
            getMetricAverage(name) {
                if (!this.metrics[name] || this.metrics[name].length === 0) {
                    return null;
                }
                return this.metrics[name].reduce((a, b) => a + b, 0) / this.metrics[name].length;
            },
            getElapsedTime() {
                return Date.now() - this.startTime;
            }
        };
    }
};

/**
 * Performance testing utilities
 */
const PerformanceUtils = {
    /**
     * Measure execution time
     */
    async measureTime(fn, label = 'Operation') {
        const startTime = Date.now();
        const result = await fn();
        const elapsed = Date.now() - startTime;
        console.log(`${label}: ${elapsed}ms`);
        return { result, elapsed };
    },

    /**
     * Benchmark function multiple times
     */
    async benchmark(fn, iterations = 100, label = 'Benchmark') {
        const times = [];
        for (let i = 0; i < iterations; i++) {
            const { elapsed } = await this.measureTime(fn, `${label} iteration ${i + 1}`);
            times.push(elapsed);
        }
        
        return {
            iterations,
            min: Math.min(...times),
            max: Math.max(...times),
            avg: times.reduce((a, b) => a + b, 0) / times.length,
            total: times.reduce((a, b) => a + b, 0),
            times
        };
    }
};

/**
 * Assertion helpers
 */
const Assertions = {
    /**
     * Assert embedding is valid 192D
     */
    assertValid192dEmbedding(embedding) {
        expect(Array.isArray(embedding)).toBe(true);
        expect(embedding.length).toBe(192);
        expect(embedding.every(val => Number.isFinite(val))).toBe(true);
    },

    /**
     * Assert similarity in valid range
     */
    assertValidSimilarity(similarity) {
        expect(typeof similarity).toBe('number');
        expect(similarity).toBeGreaterThanOrEqual(0);
        expect(similarity).toBeLessThanOrEqual(1);
    },

    /**
     * Assert result object structure
     */
    assertResultStructure(result, expectedProperties) {
        expectedProperties.forEach(prop => {
            expect(result).toHaveProperty(prop);
        });
    }
};

module.exports = {
    EmbeddingFixtures,
    Mocks,
    TestData,
    TestUtils,
    PerformanceUtils,
    Assertions,
    // Helper functions
    createTestEmbedding: () => EmbeddingFixtures.validEmbedding192d(),
    createMockLogger: () => Mocks.createMockLogger(),
    createTestContext: () => TestUtils.createTestContext()
};
