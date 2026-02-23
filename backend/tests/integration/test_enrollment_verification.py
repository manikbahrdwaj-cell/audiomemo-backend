#!/usr/bin/env python3
"""
Comprehensive Test: Enroll 3 People and Verify with Database & Similarity Function
Tests enrollment of 1 male, 1 female, 1 child with database verification and similarity testing
"""

import requests
import json
import os
import sys
from pathlib import Path

# Add backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from voice_embedding import generate_embedding, calculate_cosine_similarity
from database import (
    get_database,
    store_voice_embedding,
    check_enrollment,
    get_voice_embedding,
)
import soundfile as sf
import numpy as np

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_AUDIO_DIR = Path(__file__).parent / "test_audio_files"

# Test subjects with different characteristics
TEST_SUBJECTS = {
    "1": {
        "name": "Speaker 1 (Male)",
        "phone": "+1-555-0001",
        "enroll_file": "test_speaker1_enroll.wav",
        "verify_file": "test_speaker1_verify.wav"
    },
    "2": {
        "name": "Speaker 2 (Female)",
        "phone": "+1-555-0002",
        "enroll_file": "test_speaker2_enroll.wav",
        "verify_file": "test_speaker2_verify.wav"
    },
    "3": {
        "name": "Speaker 3 (Child)",
        "phone": "+1-555-0003",
        "enroll_file": "test_speaker3_enroll.wav",
        "verify_file": "test_speaker3_verify.wav"
    }
}

class TestResults:
    """Track test results"""
    def __init__(self):
        self.enrollments = []
        self.database_checks = []
        self.verifications = []
        self.similarity_scores = []
        
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("COMPREHENSIVE TEST RESULTS SUMMARY")
        print("="*80)
        
        print("\n1. ENROLLMENT RESULTS:")
        print("-" * 80)
        for result in self.enrollments:
            status = "✓ SUCCESS" if result['success'] else "✗ FAILED"
            print(f"{status} | {result['name']:30} | Phone: {result['phone']}")
            if result['success']:
                print(f"         | Vector ID: {result['vector_id']}")
        
        print("\n2. DATABASE VERIFICATION:")
        print("-" * 80)
        for result in self.database_checks:
            status = "✓ FOUND" if result['found'] else "✗ NOT FOUND"
            print(f"{status} | {result['name']:30} | Phone: {result['phone']}")
            if result['found']:
                print(f"         | Embedding Dimension: {result['dimension']}")
                print(f"         | MongoDB ID: {result['mongo_id']}")
        
        print("\n3. VOICE VERIFICATION (API):")
        print("-" * 80)
        for result in self.verifications:
            status = "✓ MATCH" if result['is_match'] else "○ NO MATCH"
            print(f"{status} | {result['name']:30} | Score: {result['similarity_score']:.4f}")
            print(f"         | Threshold: {result['threshold']:.2f}")
        
        print("\n4. SIMILARITY SCORES (Direct Comparison):")
        print("-" * 80)
        print(f"{'Subject':<35} | {'Similarity Score':<20}")
        print("-" * 80)
        for result in self.similarity_scores:
            print(f"{result['name']:<35} | {result['score']:.4f}")
        
        print("\n5. CROSS-SPEAKER SIMILARITY (Verification):")
        print("-" * 80)
        if len(self.similarity_scores) >= 2:
            scores = self.similarity_scores
            print(f"Speaker 1 vs Speaker 2: {scores[1].get('cross_1_2', 'N/A'):.4f}" if 'cross_1_2' in scores[1] else "N/A")
            print(f"Speaker 1 vs Speaker 3: {scores[2].get('cross_1_3', 'N/A'):.4f}" if 'cross_1_3' in scores[2] else "N/A")
            print(f"Speaker 2 vs Speaker 3: {scores[2].get('cross_2_3', 'N/A'):.4f}" if 'cross_2_3' in scores[2] else "N/A")
        
        print("\n" + "="*80)


def test_enrollment(subject_key, subject_info):
    """Test enrollment via API"""
    print(f"\n[ENROLLMENT] Testing {subject_info['name']}...")
    
    audio_path = TEST_AUDIO_DIR / subject_info['enroll_file']
    
    if not audio_path.exists():
        print(f"  ✗ Audio file not found: {audio_path}")
        return {
            'success': False,
            'name': subject_info['name'],
            'phone': subject_info['phone'],
            'vector_id': None
        }
    
    try:
        with open(audio_path, 'rb') as f:
            files = {'file': f}
            data = {'phone_number': subject_info['phone']}
            
            response = requests.post(
                f"{API_BASE_URL}/enroll",
                files=files,
                data=data
            )
        
        if response.status_code == 200:
            result_data = response.json()
            print(f"  ✓ Enrollment successful")
            print(f"    Vector ID: {result_data.get('vector_id')}")
            return {
                'success': True,
                'name': subject_info['name'],
                'phone': subject_info['phone'],
                'vector_id': result_data.get('vector_id')
            }
        else:
            print(f"  ✗ Enrollment failed: {response.status_code}")
            print(f"    Response: {response.text}")
            return {
                'success': False,
                'name': subject_info['name'],
                'phone': subject_info['phone'],
                'vector_id': None
            }
    
    except Exception as e:
        print(f"  ✗ Error during enrollment: {str(e)}")
        return {
            'success': False,
            'name': subject_info['name'],
            'phone': subject_info['phone'],
            'vector_id': None
        }


def test_database_enrollment(subject_key, subject_info):
    """Check if enrollment exists in MongoDB"""
    print(f"\n[DATABASE] Checking {subject_info['name']} in MongoDB...")
    
    try:
        is_enrolled = check_enrollment(subject_info['phone'])
        
        if is_enrolled:
            # Get the embedding details
            embedding = get_voice_embedding(subject_info['phone'])
            
            if embedding is not None:
                embedding_array = np.array(embedding)
                dimension = embedding_array.shape[0] if embedding_array.ndim > 0 else len(embedding)
                
                # Get the MongoDB document directly
                collection = get_database()
                doc = collection.find_one({'phone_number': subject_info['phone']})
                mongo_id = doc['_id'] if doc else None
                
                print(f"  ✓ Found in database")
                print(f"    Embedding Dimension: {dimension}")
                print(f"    MongoDB ID: {mongo_id}")
                return {
                    'found': True,
                    'name': subject_info['name'],
                    'phone': subject_info['phone'],
                    'dimension': dimension,
                    'mongo_id': str(mongo_id)
                }
        
        print(f"  ✗ Not found in database")
        return {
            'found': False,
            'name': subject_info['name'],
            'phone': subject_info['phone'],
            'dimension': None,
            'mongo_id': None
        }
    
    except Exception as e:
        print(f"  ✗ Error checking database: {str(e)}")
        return {
            'found': False,
            'name': subject_info['name'],
            'phone': subject_info['phone'],
            'dimension': None,
            'mongo_id': None
        }


def test_verification_api(subject_info):
    """Test verification via API"""
    print(f"\n[VERIFICATION] Testing {subject_info['name']}...")
    
    audio_path = TEST_AUDIO_DIR / subject_info['verify_file']
    
    if not audio_path.exists():
        print(f"  ✗ Verification audio not found: {audio_path}")
        return None
    
    try:
        with open(audio_path, 'rb') as f:
            files = {'file': f}
            data = {'phone_number': subject_info['phone']}
            
            response = requests.post(
                f"{API_BASE_URL}/verify",
                files=files,
                data=data
            )
        
        if response.status_code == 200:
            result_data = response.json()
            is_match = result_data.get('is_match', False)
            similarity_score = result_data.get('similarity_score', 0.0)
            threshold = result_data.get('threshold', 0.75)
            
            status = "✓ MATCH" if is_match else "○ NO MATCH"
            print(f"  {status}")
            print(f"    Similarity Score: {similarity_score:.4f}")
            print(f"    Threshold: {threshold:.2f}")
            
            return {
                'success': True,
                'name': subject_info['name'],
                'phone': subject_info['phone'],
                'is_match': is_match,
                'similarity_score': similarity_score,
                'threshold': threshold
            }
        else:
            print(f"  ✗ Verification failed: {response.status_code}")
            print(f"    Response: {response.text}")
            return None
    
    except Exception as e:
        print(f"  ✗ Error during verification: {str(e)}")
        return None


def test_similarity_scores(subject_key, subject_info):
    """Test direct similarity calculation between embeddings"""
    print(f"\n[SIMILARITY] Calculating scores for {subject_info['name']}...")
    
    verify_path = TEST_AUDIO_DIR / subject_info['verify_file']
    
    if not verify_path.exists():
        print(f"  ✗ Verification audio not found: {verify_path}")
        return None
    
    try:
        # Generate embedding from verification audio
        with open(verify_path, 'rb') as f:
            verify_audio = f.read()
        
        verify_embedding = generate_embedding(verify_audio)
        stored_embedding = np.array(get_voice_embedding(subject_info['phone']))
        
        # Calculate similarity
        similarity = calculate_cosine_similarity(verify_embedding, stored_embedding)
        
        print(f"  ✓ Similarity score calculated: {similarity:.4f}")
        
        return {
            'subject_key': subject_key,
            'name': subject_info['name'],
            'phone': subject_info['phone'],
            'score': similarity
        }
    
    except Exception as e:
        print(f"  ✗ Error calculating similarity: {str(e)}")
        return None


def test_cross_speaker_similarity():
    """Test similarity between different speakers to verify separation"""
    print(f"\n[CROSS-SPEAKER] Testing speaker differentiation...")
    
    try:
        speakers_embeddings = {}
        for key, subject in TEST_SUBJECTS.items():
            verify_path = TEST_AUDIO_DIR / subject['verify_file']
            with open(verify_path, 'rb') as f:
                verify_audio = f.read()
            speakers_embeddings[key] = {
                'name': subject['name'],
                'embedding': generate_embedding(verify_audio)
            }
        
        # Test cross-speaker similarity
        if len(speakers_embeddings) >= 2:
            keys = list(speakers_embeddings.keys())
            
            for i in range(len(keys)):
                for j in range(i + 1, len(keys)):
                    key1, key2 = keys[i], keys[j]
                    emb1 = speakers_embeddings[key1]['embedding']
                    emb2 = speakers_embeddings[key2]['embedding']
                    
                    similarity = calculate_cosine_similarity(emb1, emb2)
                    name1 = speakers_embeddings[key1]['name']
                    name2 = speakers_embeddings[key2]['name']
                    
                    print(f"  {name1} vs {name2}: {similarity:.4f}")
    
    except Exception as e:
        print(f"  ✗ Error in cross-speaker test: {str(e)}")


def main():
    """Run comprehensive test suite"""
    print("\n" + "="*80)
    print("COMPREHENSIVE VOICE BIOMETRIC TEST")
    print("Enrolling 3 Different Speakers and Verifying with Database")
    print("="*80)
    
    results = TestResults()
    
    # Step 1: Enroll all three speakers
    print("\n" + "="*80)
    print("STEP 1: ENROLLMENT")
    print("="*80)
    for key, subject in TEST_SUBJECTS.items():
        enrollment_result = test_enrollment(key, subject)
        results.enrollments.append(enrollment_result)
    
    # Step 2: Verify enrollment in database
    print("\n" + "="*80)
    print("STEP 2: DATABASE VERIFICATION")
    print("="*80)
    for key, subject in TEST_SUBJECTS.items():
        db_result = test_database_enrollment(key, subject)
        results.database_checks.append(db_result)
    
    # Step 3: Verify via API endpoint
    print("\n" + "="*80)
    print("STEP 3: API VERIFICATION")
    print("="*80)
    for key, subject in TEST_SUBJECTS.items():
        verify_result = test_verification_api(subject)
        if verify_result:
            results.verifications.append(verify_result)
    
    # Step 4: Direct similarity score calculation
    print("\n" + "="*80)
    print("STEP 4: DIRECT SIMILARITY CALCULATION")
    print("="*80)
    for key, subject in TEST_SUBJECTS.items():
        similarity_result = test_similarity_scores(key, subject)
        if similarity_result:
            results.similarity_scores.append(similarity_result)
    
    # Step 5: Cross-speaker similarity test
    print("\n" + "="*80)
    print("STEP 5: CROSS-SPEAKER DIFFERENTIATION")
    print("="*80)
    test_cross_speaker_similarity()
    
    # Print comprehensive results
    results.print_summary()
    
    # Export results to JSON
    export_results(results)


def export_results(results):
    """Export test results to JSON"""
    try:
        output_file = Path(__file__).parent / "test_results_enrollment_verification.json"
        
        export_data = {
            "test_summary": {
                "total_enrollments": len(results.enrollments),
                "successful_enrollments": sum(1 for e in results.enrollments if e['success']),
                "total_database_checks": len(results.database_checks),
                "found_in_database": sum(1 for d in results.database_checks if d['found']),
                "total_verifications": len(results.verifications),
                "successful_matches": sum(1 for v in results.verifications if v['is_match'])
            },
            "enrollments": results.enrollments,
            "database_checks": results.database_checks,
            "verifications": results.verifications,
            "similarity_scores": results.similarity_scores
        }
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"\n✓ Test results exported to: {output_file}")
    
    except Exception as e:
        print(f"\n✗ Error exporting results: {str(e)}")


if __name__ == "__main__":
    main()
