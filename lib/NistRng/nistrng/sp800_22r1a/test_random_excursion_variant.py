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

class RandomExcursionVariantTest(Test):
    def __init__(self):
        super(RandomExcursionVariantTest, self).__init__("Random Excursion Variant", 0.01)

    def _execute(self, bits: numpy.ndarray) -> Result:
        try:
            # Convert all zeros to -1
            bits_copy = bits.copy()
            bits_copy[bits_copy == 0] = -1
            
            # Generate cumulative sum with zeros at start and end
            sum_prime = numpy.concatenate((numpy.array([0]), numpy.cumsum(bits_copy), numpy.array([0]))).astype(int)
            
            # Find indices where sum_prime == 0 (cycle boundaries)
            zero_indices = numpy.where(sum_prime == 0)[0]
            
            # Count cycles (must have at least 2 zeros for one cycle)
            cycles_size = max(0, len(zero_indices) - 1)
            
            # Check minimum cycles requirement
            if cycles_size < 500:
                return Result(self.name, False, numpy.zeros(18))
            
            # Define all states to check (-9 to +9, excluding 0)
            states = list(range(-9, 0)) + list(range(1, 10))
            p_values = []
            
            for state in states:
                # Count occurrences of state in the entire sequence
                count = numpy.sum(sum_prime == state)
                
                # Calculate denominator with protection against invalid values
                denominator_term = (4.0 * abs(state)) - 2.0
                if denominator_term <= 0 or cycles_size <= 0:
                    p_values.append(0.0)
                    continue
                    
                denominator = math.sqrt(2.0 * cycles_size * denominator_term)
                if denominator == 0:
                    p_values.append(0.0)
                    continue
                
                # Calculate test statistic ξ
                ξ = abs(count - cycles_size) / denominator
                
                # Calculate p-value using complementary error function
                p_value = scipy.special.erfc(ξ / math.sqrt(2))
                p_values.append(p_value)
            
            # Convert to numpy array and check results
            p_values_array = numpy.array(p_values)
            
            # Check if any p-value is NaN and handle it
            if numpy.any(numpy.isnan(p_values_array)):
                return Result(self.name, False, numpy.zeros(18))
                
            if numpy.all(p_values_array >= self.significance_value):
                return Result(self.name, True, p_values_array)
            return Result(self.name, False, p_values_array)
            
        except Exception as e:
            # Return failure in case of any error
            return Result(self.name, False, numpy.zeros(18))

    def is_eligible(self, bits: numpy.ndarray) -> bool:
        # Sequence should be long enough for this test
        return bits.size >= 1000000  # Минимум 1 млн бит