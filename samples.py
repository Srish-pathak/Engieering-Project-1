"""Ready-made test cases for the demo. Each one is built to show a specific feature."""

SAMPLES = {
    "Python": {
        "Wrong function calls": '''def calculate_total(price, quantity, discount=0):
    return price * quantity - discount


def average(numbers):
    return sum(numbers) / len(numbers)


print(calculate_total(100))
print(calculate_total(100, 2, discount=5))
print(average([4, 8, 15]))
print(totl)
''',
        "Common mistakes": '''import os
import json


def add_item(item, items=[]):
    items.append(item)
    return items


def read_number(text):
    try:
        value = int(text)
    except:
        pass
    ratio = 10 / 0
    if value == None:
        return 0
    return value
    print("finished")
''',
        "Clean code": '''def fibonacci(n: int) -> list[int]:
    """Return the first n Fibonacci numbers."""
    if n < 0:
        raise ValueError("n must not be negative")
    numbers = []
    a, b = 0, 1
    for _ in range(n):
        numbers.append(a)
        a, b = b, a + b
    return numbers


if __name__ == "__main__":
    print(fibonacci(10))
''',
        "Syntax error": '''def greet(name)
    print("Hello", name)

greet("Asha")
''',
        "High complexity": '''def grade(score, attendance, extra):
    if score >= 90:
        if attendance > 75:
            return "A"
        elif extra:
            return "A-"
        else:
            return "B"
    elif score >= 75:
        for bonus in range(3):
            if extra and attendance > 60 or bonus == 2:
                return "B"
        return "C"
    elif score >= 50:
        while attendance < 75 and extra:
            attendance += 5
        return "C" if attendance >= 75 else "D"
    return "F"
''',
    },
    "C++": {
        "Unsafe C functions": '''#include <cstdio>
#include <cstring>

int main() {
    char name[8];
    scanf("%s", name);
    strcpy(name, "a very long default name");
    int unused = 3;
    int* data = new int[10];
    int average = 100 / 0;
    return 0;
}
''',
        "Missing semicolon": '''#include <iostream>

int add(int a, int b) {
    return a + b
}

int main() {
    std::cout << add(2, 3) << std::endl;
    return 0;
}
''',
        "Clean code": '''#include <iostream>
#include <vector>

int sum(const std::vector<int>& values) {
    int total = 0;
    for (int v : values) {
        total += v;
    }
    return total;
}

int main() {
    std::vector<int> numbers = {1, 2, 3, 4};
    std::cout << sum(numbers) << std::endl;
    return 0;
}
''',
        "Branch heavy": '''#include <iostream>

int classify(int a, int b, int c) {
    if (a > 0 && b > 0) {
        if (c > 0 || a > b) {
            return 1;
        }
        for (int i = 0; i < a; i++) {
            if (i % 2 == 0) {
                b += i;
            }
        }
        return 2;
    }
    switch (c) {
        case 1: return 3;
        case 2: return 4;
        default: return 0;
    }
}
''',
    },
    "Java": {
        "Common mistakes": '''import java.util.List;

public class Checker {
    public static boolean isAdmin(String role) {
        if (role == "admin") {
            return true;
        }
        return false;
    }

    public static int ratio(int total) {
        try {
            return total / 0;
        } catch (Exception e) {
        }
        return 0;
    }
}
''',
        "Missing semicolon": '''public class Hello {
    public static void main(String[] args) {
        int count = 5
        System.out.println(count);
    }
}
''',
        "Clean code": '''public class Counter {
    private int count;

    public void increment() {
        count++;
    }

    public int getCount() {
        return count;
    }

    public static void main(String[] args) {
        Counter counter = new Counter();
        counter.increment();
        System.out.println(counter.getCount());
    }
}
''',
    },
}


def default_sample(language):
    """First sample is shown when the app opens or the language changes."""
    return next(iter(SAMPLES[language]))
