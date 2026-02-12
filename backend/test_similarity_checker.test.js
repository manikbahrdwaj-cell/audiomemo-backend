/**
 * Unit Tests for Similarity Checker Utilities (Phase 4, Step 4.1)
 * Tests for similarity-checker.js embedding comparison functions
 */

const SimilarityChecker = require('./similarity-checker');

describe('SimilarityChecker - Initialization', () => {
    test('should initialize with default configuration', () => {
        const checker = new SimilarityChecker();
        const config = checker.getConfig();
        
        expect(config.embeddingDimension).toBe(192);
        expect(config.similarityThreshold).toBe(0.75);
        expect(config.minSimilarityThreshold).toBe(0.5);
        expect(config.maxSimilarityThreshold).toBe(1.0);
    });

    test('should initialize with custom configuration', () => {
        const customConfig = {
            embeddingDimension: 256,
            similarityThreshold: 0.8
        };
        const checker = new SimilarityChecker(customConfig);
        const config = checker.getConfig();
        
        expect(config.embeddingDimension).toBe(256);
        expect(config.similarityThreshold).toBe(0.8);
    });

    test('should merge custom config with defaults', () => {
        const customConfig = { similarityThreshold: 0.85 };
        const checker = new SimilarityChecker(customConfig);
        const config = checker.getConfig();
        
        expect(config.embeddingDimension).toBe(192);
        expect(config.similarityThreshold).toBe(0.85);
    });
});

describe('SimilarityChecker - validateEmbedding', () => {
    let checker;

    beforeEach(() => {
        checker = new SimilarityChecker();
    });

    test('should validate correct 192-dimensional embedding', () => {
        const embedding = Array(192).fill(0.5);
        const result = checker.validateEmbedding(embedding);
        
        expect(result.isValid).toBe(true);
        expect(result.dimension).toBe(192);
        expect(result.hasNaN).toBe(false);
        expect(result.hasInfinity).toBe(false);
    });

    test('should reject null embedding', () => {
        const result = checker.validateEmbedding(null);
        
        expect(result.isValid).toBe(false);
        expect(result.message).toContain('null or undefined');
    });

    test('should reject undefined embedding', () => {
        const result = checker.validateEmbedding(undefined);
        
        expect(result.isValid).toBe(false);
    });

    test('should reject non-array embedding', () => {
        const result = checker.validateEmbedding({ length: 192 });
        
        expect(result.isValid).toBe(false);
        expect(result.message).toContain('must be an array');
    });

    test('should reject empty embedding', () => {
        const result = checker.validateEmbedding([]);
        
        expect(result.isValid).toBe(false);
        expect(result.message).toContain('empty');
    });

    test('should reject incorrect dimension', () => {
        const embedding = Array(96).fill(0.5);  // Wrong dimension
        const result = checker.validateEmbedding(embedding);
        
        expect(result.isValid).toBe(false);
        expect(result.message).toContain('incorrect dimension');
        expect(result.dimension).toBe(96);
    });

    test('should reject embedding with NaN values', () => {
        const embedding = Array(192).fill(0.5);
        embedding[50] = NaN;
        const result = checker.validateEmbedding(embedding);
        
        expect(result.isValid).toBe(false);
        expect(result.hasNaN).toBe(true);
    });

    test('should reject embedding with Infinity values', () => {
        const embedding = Array(192).fill(0.5);
        embedding[75] = Infinity;
        const result = checker.validateEmbedding(embedding);
        
        expect(result.isValid).toBe(false);
        expect(result.hasInfinity).toBe(true);
    });

    test('should reject embedding with negative Infinity', () => {
        const embedding = Array(192).fill(0.5);
        embedding[100] = -Infinity;
        const result = checker.validateEmbedding(embedding);
        
        expect(result.isValid).toBe(false);
        expect(result.hasInfinity).toBe(true);
    });

    test('should accept embedding with negative values', () => {
        const embedding = Array(192).fill(-0.5);
        const result = checker.validateEmbedding(embedding);
        
        expect(result.isValid).toBe(true);
    });

    test('should accept embedding with mixed positive/negative', () => {
        const embedding = Array(96).fill(0.5).concat(Array(96).fill(-0.5));
        const result = checker.validateEmbedding(embedding);
        
        expect(result.isValid).toBe(true);
    });

    test('should include custom name in error messages', () => {
        const result = checker.validateEmbedding(null, 'enrolledEmbedding');
        
        expect(result.message).toContain('enrolledEmbedding');
    });
});

describe('SimilarityChecker - calculateL2Norm', () => {
    let checker;

    beforeEach(() => {
        checker = new SimilarityChecker();
    });

    test('should calculate L2 norm of unit vector', () => {
        const embedding = [1, 0, 0];
        const norm = checker.calculateL2Norm(embedding);
        
        expect(norm).toBeCloseTo(1.0);
    });

    test('should calculate L2 norm of zero vector', () => {
        const embedding = [0, 0, 0, 0];
        const norm = checker.calculateL2Norm(embedding);
        
        expect(norm).toBeCloseTo(0.0);
    });

    test('should calculate L2 norm correctly', () => {
        const embedding = [3, 4];
        const norm = checker.calculateL2Norm(embedding);
        
        expect(norm).toBeCloseTo(5.0);
    });

    test('should handle 192-dimensional vector', () => {
        const embedding = Array(192).fill(1);
        const norm = checker.calculateL2Norm(embedding);
        
        expect(norm).toBeCloseTo(Math.sqrt(192));
    });

    test('should ignore non-finite values', () => {
        const embedding = [1, 0, NaN, 0, Infinity];
        const norm = checker.calculateL2Norm(embedding);
        
        // Only counts the finite values: sqrt(1^2 + 0^2 + 0^2) = 1
        expect(norm).toBeCloseTo(1.0);
    });
});

describe('SimilarityChecker - calculateDotProduct', () => {
    let checker;

    beforeEach(() => {
        checker = new SimilarityChecker();
    });

    test('should calculate dot product of parallel vectors', () => {
        const a = [1, 2, 3];
        const b = [1, 2, 3];
        const dot = checker.calculateDotProduct(a, b);
        
        expect(dot).toBe(14);  // 1*1 + 2*2 + 3*3
    });

    test('should calculate dot product of orthogonal vectors', () => {
        const a = [1, 0, 0];
        const b = [0, 1, 0];
        const dot = checker.calculateDotProduct(a, b);
        
        expect(dot).toBeCloseTo(0.0);
    });

    test('should calculate dot product of opposite vectors', () => {
        const a = [1, 2];
        const b = [-1, -2];
        const dot = checker.calculateDotProduct(a, b);
        
        expect(dot).toBe(-5);
    });

    test('should handle 192-dimensional vectors', () => {
        const a = Array(192).fill(1);
        const b = Array(192).fill(1);
        const dot = checker.calculateDotProduct(a, b);
        
        expect(dot).toBe(192);
    });

    test('should ignore non-finite values', () => {
        const a = [1, 2, NaN, 4];
        const b = [2, 3, 4, Infinity];
        const dot = checker.calculateDotProduct(a, b);
        
        // Only counts finite values: 1*2 + 2*3 = 8
        expect(dot).toBe(8);
    });
});

describe('SimilarityChecker - calculateSimilarity', () => {
    let checker;

    beforeEach(() => {
        checker = new SimilarityChecker();
    });

    test('should calculate similarity of identical vectors', () => {
        const embedding1 = Array(192).fill(0.5);
        const embedding2 = Array(192).fill(0.5);
        const result = checker.calculateSimilarity(embedding1, embedding2);
        
        expect(result.isValid).toBe(true);
        expect(result.similarity).toBeCloseTo(1.0);
    });

    test('should calculate similarity of orthogonal vectors', () => {
        const embedding1 = [1, 0, 0, 0];
        const embedding2 = [0, 1, 0, 0];
        const result = checker.calculateSimilarity(embedding1, embedding2);
        
        expect(result.isValid).toBe(true);
        expect(result.similarity).toBeCloseTo(0.5);  // (0 + 1) / 2
    });

    test('should calculate similarity of opposite vectors', () => {
        const embedding1 = [1, 1, 1, 1];
        const embedding2 = [-1, -1, -1, -1];
        const result = checker.calculateSimilarity(embedding1, embedding2);
        
        expect(result.isValid).toBe(true);
        expect(result.similarity).toBeCloseTo(0.0);  // (-1 + 1) / 2
    });

    test('should return similarity in [0, 1] range', () => {
        const embedding1 = Array(192).fill(Math.random());
        const embedding2 = Array(192).fill(Math.random());
        const result = checker.calculateSimilarity(embedding1, embedding2);
        
        expect(result.similarity).toBeGreaterThanOrEqual(0);
        expect(result.similarity).toBeLessThanOrEqual(1);
    });

    test('should handle zero norm vectors', () => {
        const embedding1 = Array(4).fill(0);
        const embedding2 = Array(4).fill(0.5);
        const result = checker.calculateSimilarity(embedding1, embedding2);
        
        expect(result.isValid).toBe(false);
        expect(result.message).toContain('zero magnitude');
    });

    test('should validate embeddings when enabled', () => {
        const checker2 = new SimilarityChecker({ validationEnabled: true });
        const embedding1 = Array(192).fill(0.5);
        const embedding2 = Array(100).fill(0.5);  // Wrong dimension
        
        const result = checker2.calculateSimilarity(embedding1, embedding2);
        
        expect(result.isValid).toBe(false);
        expect(result.validation).toBeDefined();
    });

    test('should skip validation when disabled', () => {
        const checker2 = new SimilarityChecker({ validationEnabled: false });
        const embedding1 = null;
        const embedding2 = null;
        
        // Should not throw error even with invalid input when validation disabled
        expect(() => {
            checker2.calculateSimilarity(embedding1, embedding2);
        }).not.toThrow();
    });
});

describe('SimilarityChecker - compareEmbeddings', () => {
    let checker;

    beforeEach(() => {
        checker = new SimilarityChecker();
    });

    test('should detect match for identical embeddings', () => {
        const embedding1 = Array(192).fill(0.5);
        const embedding2 = Array(192).fill(0.5);
        
        const result = checker.compareEmbeddings(embedding1, embedding2);
        
        expect(result.isValid).toBe(true);
        expect(result.isMatch).toBe(true);
        expect(result.similarity).toBeCloseTo(1.0);
    });

    test('should reject match when similarity below threshold', () => {
        const embedding1 = Array(96).fill(1).concat(Array(96).fill(0));
        const embedding2 = Array(96).fill(0).concat(Array(96).fill(1));
        
        const result = checker.compareEmbeddings(embedding1, embedding2);
        
        expect(result.isValid).toBe(true);
        expect(result.isMatch).toBe(false);
    });

    test('should accept custom threshold', () => {
        const embedding1 = Array(192).fill(0.7);
        const embedding2 = Array(192).fill(0.7);
        
        const result = checker.compareEmbeddings(embedding1, embedding2, 0.9);
        
        expect(result.threshold).toBe(0.9);
        expect(result.isMatch).toBe(true);
    });

    test('should reject invalid threshold too low', () => {
        const embedding1 = Array(192).fill(0.5);
        const embedding2 = Array(192).fill(0.5);
        
        const result = checker.compareEmbeddings(embedding1, embedding2, 0.3);
        
        expect(result.isValid).toBe(false);
    });

    test('should reject invalid threshold too high', () => {
        const embedding1 = Array(192).fill(0.5);
        const embedding2 = Array(192).fill(0.5);
        
        const result = checker.compareEmbeddings(embedding1, embedding2, 1.1);
        
        expect(result.isValid).toBe(false);
    });

    test('should generate appropriate message for match', () => {
        const embedding1 = Array(192).fill(0.9);
        const embedding2 = Array(192).fill(0.9);
        
        const result = checker.compareEmbeddings(embedding1, embedding2);
        
        expect(result.isMatch).toBe(true);
        expect(result.message).toContain('match confirmed');
    });

    test('should generate appropriate message for no match', () => {
        const embedding1 = Array(96).fill(1).concat(Array(96).fill(0));
        const embedding2 = Array(96).fill(0).concat(Array(96).fill(1));
        
        const result = checker.compareEmbeddings(embedding1, embedding2);
        
        expect(result.isMatch).toBe(false);
        expect(result.message).toContain('rejected');
    });
});

describe('SimilarityChecker - compareMultipleEmbeddings', () => {
    let checker;

    beforeEach(() => {
        checker = new SimilarityChecker();
    });

    test('should find best match among multiple embeddings', () => {
        const enrolled = [
            Array(96).fill(1).concat(Array(96).fill(0)),
            Array(96).fill(0.1).concat(Array(96).fill(0.9)),
            Array(96).fill(0).concat(Array(96).fill(1))
        ];
        const verification = Array(96).fill(0).concat(Array(96).fill(1));
        
        const result = checker.compareMultipleEmbeddings(enrolled, verification);
        
        expect(result.isValid).toBe(true);
        expect(result.bestMatchIndex).toBe(2);  // Should match last enrollment
        expect(result.totalComparisons).toBe(3);
    });

    test('should handle empty enrolled embeddings', () => {
        const result = checker.compareMultipleEmbeddings([], Array(192).fill(0.5));
        
        expect(result.isValid).toBe(false);
    });

    test('should handle non-array enrolled embeddings', () => {
        const result = checker.compareMultipleEmbeddings({ length: 1 }, Array(192).fill(0.5));
        
        expect(result.isValid).toBe(false);
    });

    test('should calculate average similarity', () => {
        const enrolled = [
            Array(192).fill(0.5),
            Array(192).fill(0.5),
            Array(192).fill(0.5)
        ];
        const verification = Array(192).fill(0.5);
        
        const result = checker.compareMultipleEmbeddings(enrolled, verification);
        
        expect(result.averageSimilarity).toBeCloseTo(1.0);
    });

    test('should count matches correctly', () => {
        const enrolled = [
            Array(192).fill(0.9),
            Array(192).fill(0.1),
            Array(192).fill(0.9)
        ];
        const verification = Array(192).fill(0.9);
        
        const result = checker.compareMultipleEmbeddings(enrolled, verification, 0.75);
        
        expect(result.matchCount).toBeGreaterThan(0);
    });

    test('should track best similarity across comparisons', () => {
        const enrolled = [
            Array(96).fill(1).concat(Array(96).fill(0)),
            Array(192).fill(0.9),
            Array(96).fill(0).concat(Array(96).fill(1))
        ];
        const verification = Array(192).fill(0.9);
        
        const result = checker.compareMultipleEmbeddings(enrolled, verification);
        
        // Should identify the best matching enrollment (index 1)
        expect(result.bestSimilarity).toBeGreaterThan(0.9);
    });
});

describe('SimilarityChecker - batchCompare', () => {
    let checker;

    beforeEach(() => {
        checker = new SimilarityChecker();
    });

    test('should compare multiple verification embeddings', () => {
        const enrolled = [Array(192).fill(0.5)];
        const verifications = [
            Array(192).fill(0.5),
            Array(192).fill(0.6),
            Array(192).fill(0.4)
        ];
        
        const results = checker.batchCompare(enrolled, verifications);
        
        expect(results.length).toBe(3);
        expect(results[0].verificationIndex).toBe(0);
        expect(results[1].verificationIndex).toBe(1);
        expect(results[2].verificationIndex).toBe(2);
    });

    test('should handle non-array verifications', () => {
        const enrolled = [Array(192).fill(0.5)];
        
        const results = checker.batchCompare(enrolled, { length: 1 });
        
        expect(results.length).toBe(0);
    });

    test('should return empty for non-array input', () => {
        const results = checker.batchCompare([Array(192).fill(0.5)], "not an array");
        
        expect(results).toEqual([]);
    });
});

describe('SimilarityChecker - setThreshold', () => {
    let checker;

    beforeEach(() => {
        checker = new SimilarityChecker();
    });

    test('should set valid threshold', () => {
        const result = checker.setThreshold(0.8);
        
        expect(result).toBe(true);
        expect(checker.getConfig().similarityThreshold).toBe(0.8);
    });

    test('should reject threshold too low', () => {
        const result = checker.setThreshold(0.3);
        
        expect(result).toBe(false);
    });

    test('should reject threshold too high', () => {
        const result = checker.setThreshold(1.1);
        
        expect(result).toBe(false);
    });

    test('should accept boundary thresholds', () => {
        expect(checker.setThreshold(0.5)).toBe(true);
        expect(checker.setThreshold(1.0)).toBe(true);
    });
});

describe('SimilarityChecker - getConfig', () => {
    test('should return configuration copy', () => {
        const checker = new SimilarityChecker();
        const config1 = checker.getConfig();
        const config2 = checker.getConfig();
        
        expect(config1).toEqual(config2);
        expect(config1).not.toBe(config2);  // Should be different object reference
    });

    test('should include all default settings', () => {
        const checker = new SimilarityChecker();
        const config = checker.getConfig();
        
        expect(config).toHaveProperty('embeddingDimension');
        expect(config).toHaveProperty('similarityThreshold');
        expect(config).toHaveProperty('minSimilarityThreshold');
        expect(config).toHaveProperty('maxSimilarityThreshold');
    });
});

describe('SimilarityChecker - Edge Cases', () => {
    let checker;

    beforeEach(() => {
        checker = new SimilarityChecker();
    });

    test('should handle very small similarity values', () => {
        const embedding1 = Array(192).fill(1);
        const embedding2 = Array(96).fill(1).concat(Array(96).fill(-1));
        
        const result = checker.calculateSimilarity(embedding1, embedding2);
        
        expect(result.isValid).toBe(true);
        expect(result.similarity).toBeGreaterThanOrEqual(0);
        expect(result.similarity).toBeLessThanOrEqual(1);
    });

    test('should handle floating point precision', () => {
        const embedding1 = [0.1 + 0.2];  // Float precision issue
        const embedding2 = [0.3];
        
        // Should not throw error
        expect(() => {
            checker.calculateDotProduct(embedding1, embedding2);
        }).not.toThrow();
    });

    test('should handle many embeddings without performance issue', () => {
        const maxEmbeddings = 1000;
        const enrolled = Array(maxEmbeddings).fill(null).map(() => Array(192).fill(0.5));
        const verification = Array(192).fill(0.5);
        
        const startTime = Date.now();
        const result = checker.compareMultipleEmbeddings(enrolled, verification);
        const endTime = Date.now();
        
        expect(result.isValid).toBe(true);
        expect(endTime - startTime).toBeLessThan(5000);  // Should complete in < 5 seconds
    });
});
