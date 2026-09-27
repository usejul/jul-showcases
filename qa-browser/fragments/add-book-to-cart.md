# Fragment — get a book into the cart

Shared setup steps, reused by any ticket via `Setup : add-book-to-cart`. Only the arrange part
lives here (search, open the book, add it, reach the cart page); each ticket keeps its own act +
assertions. Every ticket that includes this runs these steps itself, so the tickets stay
independent — no test ever inherits another test's cart.

1. If a cookie banner appears, click "Accept All Cookies".
2. Search for "Theo of Golden".
3. Open the book "Theo of Golden: A Novel".
4. Click "Add To Cart".
5. Click "View Cart & Checkout".
