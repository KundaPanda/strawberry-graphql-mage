# Strawberry-GraphQL-Mage

Creates a GraphQL backend for your database with really low effort.

The mainly developed feature is currently the SQLAlchemy backend with universal dataloader support coming hopefully soon.

Performance is currently not a major factor - this is mostly a helper library to make creating GraphQL endpoints easier.

## Still under heavy development

Feel free to use it and create issues though.

Contributions are welcome as well.

## Roadmap

- [x] Generating a basic GraphQL schema
- [x] Queries
- [x] Mutations
- [ ] Subscriptions
- [x] Backend abstraction
- [ ] Move used meta attributes to an isolated Metaclass of the object instead of polluting the object with them
- [ ] SQLAlchemy backend
  - [x] Entity models
  - [x] Implement basic mutations/queries
  - [x] Add basic tests
  - [x] Filtering, ordering
  - [x] Utility functions for relationships
  - [ ] Nested pagination
  - [ ] Add more tests
  - [x] Asyncio
  - [ ] Implement abstract sqla models
- [ ] Strawberry Dataloader universal backend
  - [ ] ...
- [ ] Add more filters
- [ ] Add options for custom data-types
- [ ] Setup CI
- [ ] Try some authorization / authentication
- [ ] Write instructions for using the app
- [ ] Write instructions for creating custom backends
