#
# Copyright (C) 2019 Luca Pasqualini
# University of Siena - Artificial Intelligence Laboratory - SAILab
#
# Inspired by the work of David Johnston (C) 2017: https://github.com/dj-on-github/sp800_22_tests
#
# NistRng is licensed under a BSD 3-Clause.
#
# You should have received a copy of the license along with this
# work. If not, see <https://opensource.org/licenses/BSD-3-Clause>.

# Import packages

import numpy
import math
import scipy.special

# Import required src

from nistrng import Test, Result

class SerialTest(Test):
    def __init__(self):
        self._pattern_length: int = 4  # m = 4
        super(SerialTest, self).__init__("Serial", 0.01)

    def _execute(self, bits: numpy.ndarray) -> Result:
        """
        Serial Test implementation based on NIST SP 800-22rev1a Section 2.11
        """
        n = len(bits)
        m = self._pattern_length
        
        # Check minimum length requirement
        if n < 21 * (2 ** m):
            return Result(self.name, False, numpy.array([0.0, 0.0]))
        
        try:
            # Step 1: Extend sequence by appending first m-1 bits to the end
            extended_bits = numpy.concatenate([bits, bits[:m-1]])
            
            # Step 2: Frequency count of 2^m possible overlapping m-bit patterns
            # Using a more efficient counting method
            pattern_counts_m = self._count_patterns_efficiently(extended_bits, n, m)
            
            # Step 3: Frequency count for m-1 and m-2 bit patterns
            pattern_counts_m1 = self._count_patterns_efficiently(extended_bits, n, m-1)
            pattern_counts_m2 = self._count_patterns_efficiently(extended_bits, n, m-2)
            
            # Step 4: Compute psi-squared statistics
            psi_sq_m = self._compute_psi_squared(pattern_counts_m, n, m)
            psi_sq_m1 = self._compute_psi_squared(pattern_counts_m1, n, m-1)
            psi_sq_m2 = self._compute_psi_squared(pattern_counts_m2, n, m-2)
            
            # Step 5: Compute test statistics
            delta1 = psi_sq_m - psi_sq_m1
            delta2 = psi_sq_m - 2.0 * psi_sq_m1 + psi_sq_m2
            
            # Step 6: Compute p-values
            # Degrees of freedom according to NIST: 2^(m-1) and 2^(m-2)
            p_value1 = scipy.special.gammaincc(2 ** (m - 2), delta1 / 2.0)
            p_value2 = scipy.special.gammaincc(2 ** (m - 3), delta2 / 2.0)
            
            # Handle edge cases
            if numpy.isnan(p_value1) or numpy.isnan(p_value2):
                return Result(self.name, False, numpy.array([0.0, 0.0]))
                
            scores = numpy.array([p_value1, p_value2])
            
            if p_value1 >= self.significance_value and p_value2 >= self.significance_value:
                return Result(self.name, True, scores)
            else:
                return Result(self.name, False, scores)
                
        except Exception as e:
            return Result(self.name, False, numpy.array([0.0, 0.0]))

    def _count_patterns_efficiently(self, extended_bits: numpy.ndarray, n: int, pattern_length: int) -> numpy.ndarray:
        """
        Efficiently count all overlapping patterns of given length
        """
        if pattern_length <= 0:
            return numpy.array([])
            
        num_patterns = 2 ** pattern_length
        counts = numpy.zeros(num_patterns, dtype=int)
        
        # Convert bit sequence to integer representation for efficiency
        if pattern_length > 0:
            # Initialize the first pattern
            current_pattern = 0
            for i in range(pattern_length):
                current_pattern = (current_pattern << 1) | extended_bits[i]
            
            # Process the first pattern
            counts[current_pattern] += 1
            
            # Slide the window and update pattern
            mask = (1 << pattern_length) - 1
            for i in range(pattern_length, n + pattern_length - 1):
                if i < len(extended_bits):
                    current_pattern = ((current_pattern << 1) | extended_bits[i]) & mask
                    counts[current_pattern] += 1
        
        return counts

    def _compute_psi_squared(self, counts: numpy.ndarray, n: int, m: int) -> float:
        """
        Compute Psi-squared statistic according to NIST formula
        """
        if m <= 0 or len(counts) == 0:
            return 0.0
            
        k = len(counts)
        psi_sq = (numpy.sum(counts.astype(numpy.float64) ** 2) * k) / n - n
        
        return psi_sq

    def is_eligible(self, bits: numpy.ndarray) -> bool:
        """
        Check if sequence is long enough for the test
        """
        n = len(bits)
        m = self._pattern_length
        # NIST recommends n >= 21 * 2^m 
        return n >= 21 * (2 ** m)