# OOP Coursework Implementation Spec

This file is a practical implementation spec for the coursework project.
It is written for development agents and for the project author.
It focuses on what the codebase must contain to satisfy the coursework requirements.

---

## 1. Main goal

Build a **Python** application around one clear topic and implement it using proper **object-oriented programming**.
The code must not be a script with random functions. It must be a structured OOP project with a clear domain model, business logic, persistence, tests, and a report in Markdown.

The project should be strong enough that the report can later explain:
- what the application does,
- how to run it,
- how to use it,
- how functional requirements were implemented,
- where each OOP principle appears in the code,
- what design pattern was used,
- where composition / aggregation is used,
- how file input/output works,
- how testing was done.

---

## 2. Non-negotiable coursework requirements

The project **must** satisfy all of the following:

- The program must be written in **Python**.
- The code must follow **PEP 8** style.
- The program must implement all **4 OOP pillars**:
  - Encapsulation
  - Abstraction
  - Inheritance
  - Polymorphism
- The code must use **at least 1 design pattern**.
- The code must demonstrate **composition and/or aggregation**.
- The program must support **reading from a file and writing to a file**.
- Core functionality must be covered with **unit tests** using the **`unittest`** framework.
- A **Markdown report** is mandatory in addition to the program.

---

## 3. What the project should be about

The application must solve a real problem inside the chosen topic.
It should not only define classes; it should support meaningful user actions.

A good project should have at least these kinds of topic-specific operations:
- create/add objects,
- view/list/search objects,
- update/edit objects,
- remove/delete objects,
- save data,
- load data,
- validate incorrect input,
- show useful output to the user.

For many topics, this naturally becomes a small management system, tracker, helper tool, or game/application engine.

---

## 4. Recommended architecture

Use a structure close to this:

```text
project_root/
├─ main.py
├─ README.md
├─ report.md
├─ requirements.txt
├─ src/
│  ├─ models/
│  ├─ services/
│  ├─ storage/
│  ├─ ui/
│  ├─ factories/
│  ├─ exceptions/
│  └─ utils/
└─ tests/
```

Recommended responsibilities:

- `main.py`
  - entry point
  - starts the application
  - wires objects together

- `models/`
  - domain entities and value objects
  - examples: `User`, `Expense`, `Book`, `Reservation`, `Character`, `Task`, etc.

- `services/`
  - business logic
  - examples: add entity, validate rules, calculate totals, process commands, run game logic, filter/search

- `storage/`
  - file input/output
  - loading and saving project data
  - examples: CSV/JSON/TXT repository classes

- `ui/`
  - command-line menu, prompts, display formatting
  - should not contain business logic

- `factories/`
  - classes related to the chosen design pattern if Factory / Builder / Abstract Factory is used

- `exceptions/`
  - custom exceptions for invalid actions or invalid data

- `tests/`
  - unit tests for core behavior

---

## 5. Minimum class checklist

At minimum, the codebase should include equivalents of the following.
Exact names can change depending on the topic.

### 5.1 Domain layer

- **1 abstract or base class**
  - Example: `BaseEntity`, `Record`, `Person`, `GameObject`, `AbstractItem`
- **2 or more concrete domain classes**
  - Example: `User`, `Expense`
  - or `Book`, `Member`
  - or `Character`, `InventoryItem`

### 5.2 Business logic layer

- **1 service/controller class** responsible for main use cases
  - Example: `ExpenseService`, `LibraryService`, `GameService`, `ReservationManager`

### 5.3 Persistence layer

- **1 abstract storage/repository interface**
  - Example: `AbstractRepository`, `StorageInterface`
- **1 concrete file-based implementation**
  - Example: `CsvExpenseRepository`, `JsonLibraryRepository`, `TextSaveManager`

### 5.4 Pattern layer

- **1 explicit design pattern implementation**
  - Example: `ExpenseFactory`, `ReportBuilder`, `AppConfigSingleton`, `NotificationDecorator`

### 5.5 Error handling

- **1 or more custom exception classes**
  - Example: `ValidationError`, `NotFoundError`, `DuplicateEntityError`, `StorageError`

### 5.6 User interaction

- **1 UI/controller/menu class** if the program is interactive
  - Example: `ConsoleUI`, `MenuController`, `CLI`

---

## 6. How to satisfy the 4 OOP pillars in code

These must appear in actual code, not only in the report.

### Encapsulation

Use classes that protect their own state and validate changes.

Expected approach:
- keep attributes inside objects,
- avoid exposing raw mutable state everywhere,
- provide methods/properties for controlled updates,
- validate invalid values inside the class.

Example ideas:
- `Expense.set_amount()` rejects negative values,
- `Character.take_damage()` updates health safely,
- `Reservation.change_date()` validates conflicts.

### Abstraction

Use abstract base classes or clear interfaces for roles that can have multiple implementations.

Expected approach:
- define abstract behavior,
- let concrete subclasses implement details.

Example ideas:
- `AbstractRepository` with `save()`, `load()`, `add()`, `remove()`,
- `Notifier` with different implementations,
- `SortStrategy` / `Rule` / `Storage` abstractions.

### Inheritance

At least one class hierarchy should exist where a child class extends a parent class.

Expected approach:
- shared behavior in parent,
- specialized behavior in child classes.

Example ideas:
- `Person -> Student / Teacher`,
- `Item -> Book / MovieTicket / InventoryItem`,
- `Character -> Warrior / Mage`,
- `Repository -> CsvRepository / JsonRepository`.

### Polymorphism

Different objects should be usable through the same interface, with behavior varying by implementation.

Expected approach:
- call the same method on different subclasses or strategy objects,
- avoid long `if type == ...` chains when polymorphism can solve it.

Example ideas:
- different subclasses implement `calculate_cost()`, `display()`, `save()`, `move()`, `attack()`, etc.

---

## 7. Design pattern requirement

At least one design pattern is mandatory.

Allowed examples from the coursework brief:
- Singleton
- Factory Method
- Abstract Factory
- Builder
- Prototype
- Adapter
- Composite
- Decorator

### Recommended default choice

If there is no strong reason to choose something else, use **Factory Method**.
It is usually the safest option because it is easy to justify, easy to implement correctly, and easy to explain in the report.

### Good pattern choices by situation

- **Factory Method**
  - good when the application creates multiple object types
- **Builder**
  - good when objects require step-by-step construction
- **Singleton**
  - only use if a true single shared object makes sense
  - examples: configuration manager, app session, logger
- **Decorator**
  - good when you want to extend object behavior without changing the base class
- **Adapter**
  - good when integrating an external API or third-party structure
- **Composite**
  - good for tree-like structures such as folders, menus, grouped items

### Important rule

Do not include a fake pattern just to say a pattern exists.
The pattern must actually fit the project and be easy to explain.

---

## 8. Composition / aggregation requirement

The project must clearly show **composition and/or aggregation**.

### Composition examples

Composition means an object is built from other objects that are part of it.

Examples:
- `Library` has a collection of `Book` objects
- `Character` has `Stats`, `Inventory`, and `Health`
- `Application` has `Service`, `Repository`, and `UI`
- `Order` has `OrderItem` objects

### Aggregation examples

Aggregation means one object refers to other independent objects.

Examples:
- `Team` contains `Player` objects that can exist separately
- `GroupExpense` references multiple `User` objects
- `School` references `Teacher` and `Student` entities

### Practical recommendation

At least one main class should own or manage a collection of other objects.
That makes this requirement easy to show and easy to explain in the report.

---

## 9. File reading and writing

The program must persist data.

Minimum expectation:
- load existing data from a file,
- save current data to a file,
- handle missing/invalid/corrupted file situations gracefully.

Safe choices:
- **JSON** for structured data,
- **CSV** for table-like records,
- **TXT** only if the project is very simple.

Recommended implementation:
- define an abstract repository/storage interface,
- implement one real file-based repository,
- keep serialization logic out of UI classes.

The project should not lose user data between runs.

---

## 10. Testing requirements

Core functionality must be covered with unit tests using `unittest`.

Minimum testing targets:
- entity validation,
- service methods,
- search/filter logic,
- calculations,
- repository save/load behavior,
- error handling for invalid operations.

Recommended test structure:

```text
tests/
├─ test_models.py
├─ test_services.py
├─ test_storage.py
└─ test_integration_like_flows.py
```

Testing rules:
- test behavior, not only object creation,
- cover both success cases and failure cases,
- keep tests deterministic,
- avoid writing all logic directly inside `main.py` because that is hard to test.

---

## 11. Code style and quality rules

The project must follow **PEP 8**.

Recommended additional quality rules:
- use meaningful class and method names,
- keep classes focused on one responsibility,
- avoid giant god classes,
- avoid global mutable state,
- use type hints where practical,
- use docstrings for important public classes/methods,
- separate UI from business logic,
- separate business logic from file I/O,
- keep methods reasonably short,
- prefer clear object interactions over procedural spaghetti code.

---

## 12. Report requirements that must be supported by the code

A Markdown report is mandatory, so the codebase must make the report easy to write.

The report must contain these parts:

## Introduction
Must explain:
- what the application is,
- the goal of the coursework,
- how to run the program,
- how to use the program.

## Body / Analysis
Must explain:
- how the program implements functional requirements,
- how the OOP pillars are used,
- what design pattern was used and why,
- where composition / aggregation appears,
- how file input/output works,
- how testing was done.

## Results
Must contain:
- **3-5 bullet points / sentences** about the result,
- may include implementation challenges.

## Conclusions
Must contain:
- short summary of what was achieved,
- what result the program provides,
- future extension possibilities.

### Important implementation consequence

The code should contain clean, isolated examples of each requirement so that screenshots/snippets can easily be taken for the report.

---

## 13. Recommended “safe for grading” implementation plan

To maximize the chance of satisfying the coursework cleanly, the project should include:

1. **A clearly defined domain**
   - at least 2-4 important entity classes
2. **A service layer**
   - central use-case logic
3. **A repository/storage layer**
   - load/save data from file
4. **A visible design pattern**
   - ideally Factory Method unless another one fits better
5. **A clear composition example**
   - one object containing/managing other objects
6. **A clear inheritance hierarchy**
   - parent + specialized child classes
7. **A clear polymorphism example**
   - shared method used across different concrete types
8. **A test suite using `unittest`**
9. **A Markdown report**
10. **Simple, reliable user interaction**
   - usually a CLI menu is enough

---

## 14. Suggested concrete template for almost any topic

This template is intentionally generic and can be adapted to most coursework topics.

### Core classes

- `BaseEntity` - common ID / name / shared validation
- `AbstractRepository` - abstract save/load/add/remove interface
- `FileRepository` - actual JSON/CSV/TXT implementation
- `ProjectService` - main business logic
- `ConsoleUI` - input/output menu
- `EntityFactory` - design pattern implementation
- `ValidationError`, `NotFoundError`, `StorageError` - custom exceptions

### Example topic entities

Depending on topic, add classes such as:
- management system: `User`, `Item`, `Reservation`, `Record`
- finance tracker: `User`, `Expense`, `Category`, `Budget`
- birthday reminder: `User`, `BirthdayRecord`, `Notification`
- DND helper: `Character`, `Stats`, `InventoryItem`, `Ability`
- game: `Board`, `Player`, `Piece`, `Move`, `GameEngine`
- file manager: `FileOperation`, `CopyOperation`, `MoveOperation`, `DeleteOperation`

---

## 15. Definition of done

The project is only “done” when all items below are true:

- [ ] Program is written in Python.
- [ ] Code follows PEP 8 reasonably well.
- [ ] Topic has meaningful functionality, not just empty classes.
- [ ] All 4 OOP pillars are present in code.
- [ ] At least 1 design pattern is present and explainable.
- [ ] Composition and/or aggregation is present.
- [ ] Data can be loaded from file.
- [ ] Data can be saved to file.
- [ ] Invalid input and file errors are handled.
- [ ] Core functionality has `unittest` coverage.
- [ ] Code is split into logical modules/classes.
- [ ] Report in Markdown exists.
- [ ] Report includes introduction, body/analysis, results, conclusions.
- [ ] Report can show code examples/snippets for every important requirement.

---

## 16. Final instruction for development agents

When implementing features, always prefer decisions that make these coursework requirements easier to demonstrate explicitly.

Priority order:
1. satisfy coursework requirements,
2. keep the design clean and explainable,
3. keep the code testable,
4. keep the report easy to write.

If a design choice is elegant but makes the coursework requirements harder to prove, do **not** choose it.
