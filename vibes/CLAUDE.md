I am designing an algorithm for a game called A-Math, which is similar to English Scrabble. However, instead of forming words, players create equations using the following tile distribution:
@chars.json
Tiles marked +/- or ×/÷: The player must choose only one option: either + or −, or either × or ÷. Once chosen, it cannot be changed.
Blank tiles ? :A blank tile may represent any value from 0–20, including the operators +, −, ×, ÷, and =. Once assigned, it cannot be changed.
Rules:
	5	Combining NumbersOn each turn, players may place two or three digits, from 0–9, next to each other to form a two- or three-digit number.
Examples:
	•	Tiles 1 and 2 can form 12.
	•	Tiles 1, 8, and 5 can form 185.
	•	Tiles 1,2,3,4 cannot form 1234 as that is more than 3 digits.
	6	Using Negative Numbers
    A minus sign (−) may be placed in front of numbers from 1–20, as well as numbers created under Rule 5, to make them negative.
Examples:
	•	−6 = 4 − 10
	•	−5 = −5
	•	-123=-123
However, a plus or minus sign cannot be placed directly after another plus or minus sign.
Example:
	•	−7 = 6 + −3 ❌ Not allowed
	7	Prohibition on Leading ZerosA number may not begin with 0.
Examples:
	•	07 ❌ Not allowed
	•	012 ❌ Not allowed
	8	No + or − in Front of ZeroA plus or minus sign may not be placed in front of 0 in front of a term a or b in a=b. ( 9+0=9 is allowed, however, +0+9=9 or 9=+0+9 is not)
	9	No + in Front of an EquationA plus sign may not be placed at the beginning of an equation.
Example:
	•	+7 = 5 + 2 ❌ Not allowed


Basic Calculation Principles:
	1	Order of OperationsWhen multiplication, division, addition, and subtraction appear together, calculations must follow the correct order of operations.
Examples:
	•	8 × 3 ÷ 6 = 24 ÷ 6 = 4
	•	7 − 4 + 5 = 3 + 5 = 8
	2	Multiplication Before Addition/SubtractionMultiplication and division are always calculated before addition and subtraction.
Examples:
	•	4 × 3 + 4 = (4 × 3) + 4 = 12 + 4 = 16
	•	4 × 9 ÷ 2 + 5 = (4 × 9 ÷ 2) + 5 = 18 + 5 = 23
	3	Division by ZeroZero may not be used as a divisor. However, if 0 is used as the dividend and is divided by a non-zero number, the result is 0.
Examples:
	•	5 ÷ 0 ❌ Not allowed
	•	0 ÷ 5 = 0 ✔️
	4	Expanding Existing EquationsEquations already on the board that have no operators at the ends may be extended.
Example:
	•	From 2 × 2 + 1 = 5, you can extend it to:   2 × 2 × 2 + 1 = 5 + 4
Equations may also be extended further with the equals sign, as long as they remain balanced, including by making them symmetrical.
Examples:
	•	4 + 5 = 3 × 3 
	•	4 + 5 = 3 × 3 = 9 ÷ 1
	5	Fractional ResultsEquations may produce fractional results.
Example:
	•	2 ÷ 4 = 4 ÷ 8, since both equal 1/2.
Given a set of tiles, I want to generate all valid equations.
Input: Array of chars: 8 to 12 tiles given the tile distribution Example: [‘1’,’+’, ‘2’ , ‘-‘, ‘=‘, ‘3’, '1', '='….]
Output: List of string: valid equations Example: ["1+2=3","3-2=1","1=1=1"......]
Note: If there are no =, in the original equation then there can be no valid equation. If there are multiple = then you could hypothetically use all of them. For blank tiles and +/- type tiles, cache valid equations that have already have one of the blank values and iterate through all possible values they could take
Please create a function that takes an array of tiles and generates all valid equations as quickly as possible. It should run quite fast.
