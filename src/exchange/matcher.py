from .models import Order, Trade
from .book import OrderBook
from collections import deque

class MatchingEngine:
    """
    MatchingEngine accepts new orders and attempts to match them against the current
    top-of-book on the opposite side.

    Matching behavior (current version)
    -----------------------------------
    - Only matches against the single best price level (top-of-book).
    - Only executes a trade when the incoming order qty EXACTLY equals the resting
      top order qty at that level.
    - If prices cross but quantity does not match exactly, the order is added to the book
      (no partial fills are implemented yet).
    - After a trade, the filled resting order is removed from the book.
    - Tracks the most recent trade in _last_trade.

    Notes / Limitations
    -------------------
    - No partial fills
    - No multi-order sweeping (does not walk the book)
    - No time priority beyond FIFO within a single price level (deque)
    - Directly accesses book internals (_bids/_asks), which is OK for a toy engine but
      should be encapsulated later
    """

    def __init__(self, book: OrderBook):
        """
        Initialize the matching engine.

        Args:
            book: The OrderBook instance this engine will read from and write to.
        """
        self._last_trade: Trade | None = None
        self.book: OrderBook = book

    def submit_order(self, order: Order) -> list[Trade]:
        """
        Submit a new order to the engine.

        If the order crosses the spread and matches exactly in quantity with the
        top resting order, a Trade is produced.

        Returns:
            A list of executed trades (empty list if no trade occurs).
            Current implementation returns either [] or [trade].
        """
        if order.side == "BUY":
            # BUY order matches against the best ask (lowest ask price)
            best_ask = self.book.get_best_ask()

            # If no asks exist, place the order in the book
            if best_ask is None:
                self.book.add_order(order)
                return []

            best_ask_price = best_ask[0]

            # If the BUY price crosses the ask, attempt to match
            if order.price >= best_ask_price:
                best_ask_level: deque = self.book._asks[best_ask_price]
                best_ask_order: Order = best_ask_level[0]  # FIFO at this price

                # Only match if quantities are exactly equal (no partial fills yet)
                if order.qty == best_ask_order.qty:
                    taker_order_id = order.order_id
                    maker_order_id = best_ask_order.order_id

                    trade = Trade(
                        price=best_ask_order.price,
                        qty=order.qty,
                        taker_order_id=taker_order_id,
                        maker_order_id=maker_order_id
                    )

                    self._last_trade = trade
                    best_ask_level.popleft()  # remove filled resting order

                else:
                    # Crossed but not equal quantity -> do not match in this version
                    self.book.add_order(order)
                    return []

                # If the price level is now empty, remove it from the book
                if len(best_ask_level) == 0:
                    del self.book._asks[best_ask_price]

                return [trade]

            # If the BUY does not cross, add to book
            elif order.price < best_ask_price:
                self.book.add_order(order)
                return []

        elif order.side == "SELL":
            # SELL order matches against the best bid (highest bid price)
            best_bid = self.book.get_best_bid()

            # If no bids exist, place the order in the book
            if best_bid is None:
                self.book.add_order(order)
                return []

            best_bid_price = best_bid[0]

            # If the SELL price crosses the bid, attempt to match
            if order.price <= best_bid_price:
                best_bid_level: deque = self.book._bids[best_bid_price]
                best_bid_order: Order = best_bid_level[0]  # FIFO at this price

                # Only match if quantities are exactly equal (no partial fills yet)
                if order.qty == best_bid_order.qty:
                    taker_order_id = order.order_id
                    maker_order_id = best_bid_order.order_id

                    trade = Trade(
                        price=best_bid_price,
                        qty=order.qty,
                        taker_order_id=taker_order_id,
                        maker_order_id=maker_order_id
                    )

                    self._last_trade = trade
                    best_bid_level.popleft()  # remove filled resting order

                else:
                    # Crossed but not equal quantity -> do not match in this version
                    self.book.add_order(order)
                    return []

                # If the price level is now empty, remove it from the book
                if len(best_bid_level) == 0:
                    del self.book._bids[best_bid_price]

                return [trade]

            # If the SELL does not cross, add to book
            elif order.price > best_bid_price:
                self.book.add_order(order)
                return []

    def top_of_book(self) -> dict:
        """
        Return the current top-of-book snapshot.

        Output format:
            {
              'bid': (best_bid_price, total_qty_at_best_bid) or None,
              'ask': (best_ask_price, total_qty_at_best_ask) or None
            }
        """
        return {
            'bid': self.book.get_best_bid(),
            'ask': self.book.get_best_ask()
        }

    def last_trade(self):
        """
        Return the most recent Trade executed by this engine, or None if no trades.
        """
        return self._last_trade
