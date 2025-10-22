def number_from_hash(hash_bytes, min_val, max_val):
    range_size = max_val - min_val + 1
    max_allowed = (1 << 32) // range_size * range_size

    bit_buffer = 0
    bit_count = 0
    byte_index = 0

    while True:
        while bit_count < 32:
            bit_buffer = (bit_buffer << 8) | hash_bytes[byte_index]
            byte_index += 1
            bit_count += 8

        random_value = (bit_buffer >> (bit_count - 32)) & 0xFFFFFFFF
        bit_count -= 32
        bit_buffer &= (1 << bit_count) - 1

        if random_value < max_allowed:
            return min_val + (random_value % range_size)
