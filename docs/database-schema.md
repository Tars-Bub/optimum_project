# Database schema

Generated from the Django models, so it matches the code exactly. SQLite is used by default; the same
models create MySQL tables when the `DB_*` environment variables are set. Every table also has an
`id` primary key (auto number). `auth_user` is Django's built-in users table.

## `accounts_profile`

| Column | Type | Null | Key / rule |
|---|---|---|---|
| `id` | BigAutoField | no | PK |
| `user_id` | OneToOneField | no | unique; FK to `auth_user`.id (CASCADE) |
| `role` | varchar(10) | no | one of: staff, admin; default 'staff' |
| `position` | varchar(60) | no |  |
| `contact` | varchar(30) | no |  |
| `status` | varchar(10) | no | one of: active, inactive, pending; default 'active' |

## `catalog_category`

| Column | Type | Null | Key / rule |
|---|---|---|---|
| `id` | BigAutoField | no | PK |
| `name` | varchar(80) | no | unique |

## `catalog_product`

| Column | Type | Null | Key / rule |
|---|---|---|---|
| `id` | BigAutoField | no | PK |
| `code` | varchar(30) | no | unique |
| `name` | varchar(120) | no |  |
| `category_id` | ForeignKey | no | FK to `catalog_category`.id (PROTECT) |
| `unit_cost` | decimal(10,2) | no | default Decimal('0') |
| `price` | decimal(10,2) | no | default Decimal('0') |
| `quantity` | IntegerField | no | default 0 |
| `reorder_level` | PositiveIntegerField | no | default 10 |
| `is_active` | BooleanField | no | default True |

## `stock_stockmovement`

| Column | Type | Null | Key / rule |
|---|---|---|---|
| `id` | BigAutoField | no | PK |
| `product_id` | ForeignKey | no | FK to `catalog_product`.id (PROTECT) |
| `kind` | varchar(20) | no | one of: opening, incoming, sale, return, exchange_in, exchange_out, void, adjustment |
| `change` | IntegerField | no |  |
| `balance_after` | IntegerField | no |  |
| `reference` | varchar(60) | no |  |
| `note` | varchar(255) | no |  |
| `user_id` | ForeignKey | yes | FK to `auth_user`.id (SET_NULL) |
| `created_at` | DateTimeField | no |  |

## `sales_order`

| Column | Type | Null | Key / rule |
|---|---|---|---|
| `id` | BigAutoField | no | PK |
| `client_name` | varchar(120) | no |  |
| `client_business` | varchar(120) | no |  |
| `client_tin` | varchar(30) | no |  |
| `client_address` | varchar(255) | no |  |
| `po_number` | varchar(50) | no |  |
| `payment_terms` | varchar(60) | no |  |
| `status` | varchar(10) | no | one of: draft, finalized, voided; default 'draft' |
| `amount_paid` | decimal(12,2) | no | default Decimal('0') |
| `created_by_id` | ForeignKey | yes | FK to `auth_user`.id (SET_NULL) |
| `created_at` | DateTimeField | no |  |
| `finalized_at` | DateTimeField | yes |  |
| `voided_at` | DateTimeField | yes |  |
| `void_reason` | varchar(200) | no |  |

## `sales_orderitem`

| Column | Type | Null | Key / rule |
|---|---|---|---|
| `id` | BigAutoField | no | PK |
| `order_id` | ForeignKey | no | FK to `sales_order`.id (CASCADE) |
| `product_id` | ForeignKey | no | FK to `catalog_product`.id (PROTECT) |
| `quantity` | PositiveIntegerField | no | default 1 |
| `unit_price` | decimal(10,2) | no |  |
| `returned_qty` | PositiveIntegerField | no | default 0 |

Unique together: (order, product)

## `sales_returnrecord`

| Column | Type | Null | Key / rule |
|---|---|---|---|
| `id` | BigAutoField | no | PK |
| `order_id` | ForeignKey | no | FK to `sales_order`.id (CASCADE) |
| `kind` | varchar(10) | no | one of: return, exchange |
| `reason` | varchar(200) | no |  |
| `refund_amount` | decimal(12,2) | no | default Decimal('0') |
| `replacement_product_id` | ForeignKey | yes | FK to `catalog_product`.id (PROTECT) |
| `created_by_id` | ForeignKey | yes | FK to `auth_user`.id (SET_NULL) |
| `created_at` | DateTimeField | no |  |

## `sales_returnline`

| Column | Type | Null | Key / rule |
|---|---|---|---|
| `id` | BigAutoField | no | PK |
| `record_id` | ForeignKey | no | FK to `sales_returnrecord`.id (CASCADE) |
| `item_id` | ForeignKey | no | FK to `sales_orderitem`.id (PROTECT) |
| `quantity` | PositiveIntegerField | no |  |

## `documents_document`

| Column | Type | Null | Key / rule |
|---|---|---|---|
| `id` | BigAutoField | no | PK |
| `doc_type` | varchar(10) | no | one of: invoice, delivery |
| `number` | varchar(30) | no |  |
| `order_id` | ForeignKey | no | FK to `sales_order`.id (PROTECT) |
| `printed_by_id` | ForeignKey | yes | FK to `auth_user`.id (SET_NULL) |
| `printed_at` | DateTimeField | no |  |
| `reprint_count` | PositiveIntegerField | no | default 0 |

Unique together: (doc_type, number)

## `payments_mayapayment`

| Column | Type | Null | Key / rule |
|---|---|---|---|
| `id` | BigAutoField | no | PK |
| `order_id` | ForeignKey | no | FK to `sales_order`.id (PROTECT) |
| `reference` | varchar(64) | no | unique; our request reference number sent to Maya |
| `checkout_id` | varchar(64) | no | indexed; Maya's checkout / payment id |
| `checkout_url` | varchar(500) | no | link and QR the customer pays with |
| `amount` | decimal(12,2) | no | amount asked from the customer |
| `status` | varchar(10) | no | one of: pending, paid, failed, expired, cancelled; default 'pending' |
| `maya_status` | varchar(40) | no | last raw status from Maya, for example PAYMENT_SUCCESS |
| `note` | varchar(200) | no | warnings such as an amount mismatch |
| `created_by_id` | ForeignKey | yes | FK to `auth_user`.id (SET_NULL) |
| `created_at` | DateTimeField | no |  |
| `paid_at` | DateTimeField | yes |  |

## `core_auditlog`

| Column | Type | Null | Key / rule |
|---|---|---|---|
| `id` | BigAutoField | no | PK |
| `user_id` | ForeignKey | yes | FK to `auth_user`.id (SET_NULL) |
| `action` | varchar(60) | no |  |
| `detail` | varchar(255) | no |  |
| `created_at` | DateTimeField | no |  |

## Relationships

| From | Column | To | If the parent is deleted |
|---|---|---|---|
| `accounts_profile` | `user` | `auth_user` | CASCADE |
| `catalog_product` | `category` | `catalog_category` | PROTECT |
| `stock_stockmovement` | `product` | `catalog_product` | PROTECT |
| `stock_stockmovement` | `user` | `auth_user` | SET_NULL |
| `sales_order` | `created_by` | `auth_user` | SET_NULL |
| `sales_orderitem` | `order` | `sales_order` | CASCADE |
| `sales_orderitem` | `product` | `catalog_product` | PROTECT |
| `sales_returnrecord` | `order` | `sales_order` | CASCADE |
| `sales_returnrecord` | `replacement_product` | `catalog_product` | PROTECT |
| `sales_returnrecord` | `created_by` | `auth_user` | SET_NULL |
| `sales_returnline` | `record` | `sales_returnrecord` | CASCADE |
| `sales_returnline` | `item` | `sales_orderitem` | PROTECT |
| `documents_document` | `order` | `sales_order` | PROTECT |
| `documents_document` | `printed_by` | `auth_user` | SET_NULL |
| `payments_mayapayment` | `order` | `sales_order` | PROTECT |
| `payments_mayapayment` | `created_by` | `auth_user` | SET_NULL |
| `core_auditlog` | `user` | `auth_user` | SET_NULL |

`PROTECT` means the database refuses to delete a row that others still use (for example a product that
appears in an order). `CASCADE` deletes the dependent rows. `SET_NULL` keeps them and clears the link.
