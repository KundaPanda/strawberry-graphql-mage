# Strawberry-MAGE
A backend-agnostic automated graphql api generator.

The aim of this project is to simplify graphql api creation without being tied to one specific data backend.

## TO-DO:
- [x] Generating a basic GraphQL schema
- [x] Queries
- [x] Mutations
- [ ] Subscriptions
- [x] Backend separation + dummy backend
- [ ] SQLAlchemy backend
  - [x] Entity models
  - [x] Implement basic mutations/queries
  - [x] Add basic tests
  - [ ] Add more tests
  - [x] Asyncio
  - [ ] Implement abstract sqla models
- [ ] Python backend
  - [x] Basic SQLAlchemy conversion
  - [x] Database engine pool
  - [ ] Native python datatype simple implementation
  - [x] Queries
  - [x] Queries with dynamic dataset
  - [ ] Mutations
  - [ ] TESTS
- [ ] JSON (dict) backend
  - [x] Conversion to python backend
  - [x] Queries
  - [x] Queries with dynamic dataset
  - [ ] Mutations
  - [ ] TESTS
- [ ] API backend (REST/GraphQL)
  - [x] Queries
  - [x] Queries with dynamic dataset
  - [x] Mutations
  - [ ] Helpers for graphql input fields conversion
  - [ ] Improve the structure
  - [ ] TESTS
- [ ] Separate backends into package extras
- [ ] Add more filters
- [ ] Add options for custom data-types
- [ ] Setup CI
- [ ] Try some authorization / authentication
- [ ] Write instructions for using the app
- [ ] Write instructions for creating custom backends