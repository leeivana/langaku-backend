import random, string


def generate_str(length=10) -> string:
    return "".join(random.choices(string.ascii_letters, k=length))


def random_int(min_value: int, max_value: int) -> int:
    return random.randint(min_value, max_value)
