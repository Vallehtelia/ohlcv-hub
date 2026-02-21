# Alpaca Market Data API - Historical Stock Bars Endpoint

## Overview

This document captures the exact API contract for Alpaca Market Data API v2 historical stock bars endpoint, including parameter names, response structure, pagination semantics, and edge cases.

**Source**: [Alpaca Market Data API Reference](https://docs.alpaca.markets/reference/stockbars)

## Base URLs

- **Production**: `https://data.alpaca.markets`
- **Sandbox**: `https://data.sandbox.alpaca.markets`

## Endpoint

**Path**: `GET /v2/stocks/bars`

**Description**: Retrieves aggregated bar data for multiple stock symbols between specified dates.

## Authentication

**Required HTTP Headers**:
- `APCA-API-KEY-ID`: API key identifier
- `APCA-API-SECRET-KEY`: API secret key

**Notes**:
- Both headers are required for all requests
- Same credentials work for both paper and live accounts (determined by base URL)
- Sandbox uses `data.sandbox.alpaca.markets` for testing

## Query Parameters

### Required Parameters

#### `symbols`
- **Type**: `string`
- **Format**: Comma-separated list of stock symbols
- **Example**: `"AAPL,TSLA,MSFT"`
- **Description**: One or more stock ticker symbols to query

#### `timeframe`
- **Type**: `string`
- **Required**: Yes
- **Allowed Values**:
  - `[1-59]Min` or `[1-59]T` (e.g., `5Min`, `5T`) - minute aggregations
  - `[1-23]Hour` or `[1-23]H` (e.g., `12Hour`, `12H`) - hour aggregations
  - `1Day` or `1D` - daily aggregations
  - `1Week` or `1W` - weekly aggregations
  - `[1,2,3,4,6,12]Month` or `[1,2,3,4,6,12]M` (e.g., `3Month`, `3M`) - month aggregations
- **Example**: `"1Day"` for daily bars
- **Note**: For daily bars, use `1Day` (not `1D` is also valid, but `1Day` is more explicit)

### Optional Parameters

#### `start`
- **Type**: `string` (date-time)
- **Format**: RFC-3339 date-time (with second or nanosecond precision) OR `YYYY-MM-DD` date format
- **Examples**:
  - `"2024-01-03T00:00:00Z"` (RFC-3339 with second precision)
  - `"2024-01-03T01:02:03.123456789Z"` (RFC-3339 with nanosecond precision)
  - `"2024-01-03T09:30:00-04:00"` (RFC-3339 with timezone)
  - `"2024-01-03"` (date only)
- **Default**: Beginning of current day, but at least 15 minutes ago if user doesn't have real-time access
- **Description**: Inclusive start of the interval

#### `end`
- **Type**: `string` (date-time)
- **Format**: Same as `start` (RFC-3339 or `YYYY-MM-DD`)
- **Default**: Current time if user has real-time access, otherwise 15 minutes before current time
- **Description**: Inclusive end of the interval

#### `limit`
- **Type**: `integer`
- **Range**: 1 to 10,000
- **Default**: 1,000
- **Description**: Maximum number of data points to return in the response page
- **Critical Note**: The limit applies to the **total number of data points across all symbols**, NOT per symbol. The API may return fewer bars even if more are available—always check `next_page_token`.

#### `adjustment`
- **Type**: `string`
- **Default**: `"raw"`
- **Allowed Values**:
  - `"raw"`: No adjustments
  - `"split"`: Adjust price and volume for forward and reverse stock splits
  - `"dividend"`: Adjust price for cash dividends
  - `"spin-off"`: Adjust price for spin-offs
  - `"all"`: Apply all above adjustments
- **Combination**: Multiple adjustments can be combined with commas (e.g., `"split,spin-off"`)
- **Description**: Specifies corporate action adjustments for the bars

#### `feed`
- **Type**: `string`
- **Default**: `"sip"` (best available feed based on subscription)
- **Allowed Values**:
  - `"sip"`: All US exchanges (Securities Information Processor - consolidated tape)
  - `"iex"`: Investors Exchange only
  - `"boats"`: Blue Ocean ATS (overnight US trading data)
  - `"otc"`: Over-the-counter exchanges (requires special subscription, broker partners only)
- **Description**: Source feed of the data
- **Note**: SIP feed requires subscription for recent data (<15 minutes old). Default feed is chosen based on user's subscription level.

#### `asof`
- **Type**: `string`
- **Format**: `YYYY-MM-DD` date format
- **Default**: Current day
- **Special Value**: `"-"` (disables symbol mapping)
- **Description**: As-of date used to identify underlying entity for symbol name changes
- **Example**: Querying `META` with `asof=2022-06-10` will also return `FB` data from before the rename (FB→META happened 2022-06-09)
- **Note**: Symbol mapping is only available on historical endpoints the day after a rename

#### `currency`
- **Type**: `string`
- **Default**: `"USD"`
- **Format**: ISO 4217 currency code
- **Description**: Currency for all prices in the response

#### `page_token`
- **Type**: `string`
- **Description**: Pagination token from previous response to continue fetching more data
- **Usage**: Pass the `next_page_token` value from the previous response as `page_token` parameter

#### `sort`
- **Type**: `string`
- **Default**: `"asc"`
- **Allowed Values**: `"asc"`, `"desc"`
- **Description**: Sort data in ascending or descending order

## Response Structure

### HTTP Status Codes

- `200`: OK
- `400`: Invalid request parameters
- `401`: Authentication headers missing or invalid
- `403`: Forbidden (insufficient permissions, wrong credentials, or not authenticated)
- `429`: Rate limit exceeded
- `500`: Internal server error

### Response Headers

Rate limiting information is provided in response headers:
- `X-RateLimit-Limit`: Request limit per minute (e.g., `100`)
- `X-RateLimit-Remaining`: Remaining requests in current window (e.g., `90`)
- `X-RateLimit-Reset`: UNIX epoch timestamp when remaining quota resets (e.g., `1674044551`)
- `X-Request-ID`: Unique identifier for the API call (useful for support requests)

### Response Body (200 OK)

**Top-level structure**:
```json
{
  "bars": {
    "SYMBOL1": [
      { /* bar object */ },
      { /* bar object */ }
    ],
    "SYMBOL2": [
      { /* bar object */ }
    ]
  },
  "next_page_token": "QUFQTHxNfDIwMjItMDEtMDNUMDk6MDA6MDAuMDAwMDAwMDAwWg==",
  "currency": "USD"
}
```

**Fields**:
- `bars`: Object mapping symbol strings to arrays of bar objects
- `next_page_token`: String token for pagination (nullable, `null` if no more pages)
- `currency`: ISO 4217 currency code (optional, may be absent)

### Bar Object Structure

Each bar object contains:
```json
{
  "t": "2022-01-03T09:00:00Z",
  "o": 178.26,
  "h": 178.34,
  "l": 177.76,
  "c": 178.08,
  "v": 60937,
  "n": 1727,
  "vw": 177.954244
}
```

**Field Names and Types**:
- `t` (timestamp): `string` - RFC-3339 format with nanosecond precision (e.g., `"2022-01-03T09:00:00Z"`)
- `o` (open): `number` (double) - Opening price
- `h` (high): `number` (double) - High price
- `l` (low): `number` (double) - Low price
- `c` (close): `number` (double) - Closing price
- `v` (volume): `integer` (int64) - Bar volume
- `n` (trade count): `integer` (int64) - Number of trades in the bar
- `vw` (VWAP): `number` (double) - Volume-weighted average price

**All fields are required** in each bar object.

## Response Ordering and Pagination

### Sorting Behavior

**Critical**: Results are sorted by **symbol first, then by bar timestamp** (ascending by default, or descending if `sort=desc`).

**Implication**: When requesting multiple symbols, if one symbol has enough bars to hit the `limit`, you may only see that one symbol in the first response. You must paginate using `next_page_token` to retrieve bars for other symbols.

**Example Scenario**:
- Request: `symbols=AAPL,TSLA&limit=1000&timeframe=1Day&start=2020-01-01&end=2024-01-01`
- If AAPL has 1000+ daily bars in this range, the first response may contain only AAPL bars
- Use `page_token` from `next_page_token` to fetch TSLA bars in subsequent requests

### Pagination Flow

1. Make initial request with `symbols`, `timeframe`, `start`, `end`, `limit`
2. Check response for `next_page_token`
3. If `next_page_token` is not `null`, make another request with same parameters plus `page_token=<next_page_token>`
4. Repeat until `next_page_token` is `null`

**Important**: The `limit` applies globally across all symbols, not per symbol. Pagination is necessary to retrieve all bars for all symbols when the total exceeds the limit.

## Rate Limits

- Rate limits are per-minute
- Exact limits depend on subscription level
- Check `X-RateLimit-*` headers in responses
- HTTP 429 is returned when rate limit is exceeded
- Default appears to be around 100 requests/minute (verify with actual API calls)

## Edge Cases and Pitfalls

### 1. Pagination Across Multiple Symbols

**Issue**: Due to symbol-first sorting, pagination can be confusing when querying multiple symbols.

**Mitigation**: 
- Track which symbols have been fully retrieved
- Continue paginating until `next_page_token` is `null`
- Consider querying symbols individually if you need guaranteed per-symbol completeness

### 2. Timezone Normalization

**Issue**: Alpaca returns timestamps in RFC-3339 format (typically UTC, e.g., `"2022-01-03T09:00:00Z"`). Daily bars appear to use `04:00:00Z` (midnight ET) as the bar timestamp.

**Recommendation**: 
- Store timestamps as UTC
- For weekly resampling, decide on timestamp policy (Monday 00:00 UTC vs first trading day)
- Document timezone assumptions in code

### 3. Corporate Action Adjustments

**Issue**: The `adjustment` parameter semantics:
- `"all"` applies split, dividend, and spin-off adjustments
- Adjusted prices reflect historical prices as if corporate actions never happened
- Volume may also be adjusted for splits

**Recommendation**: 
- Use `adjustment="all"` for backtesting/analysis
- Use `adjustment="raw"` for actual trading prices
- Document which adjustment is used in output files

### 4. Missing Days / Holidays

**Issue**: No bars are returned for non-trading days (holidays, weekends). Partial trading days may have bars with reduced volume.

**Mitigation**: 
- Use trading calendar library (e.g., `pandas_market_calendars`) to identify expected trading days
- Compare retrieved bars against expected trading days to detect data gaps
- Report missing days separately from delisted symbols

### 5. Data Gaps / Delisted Symbols

**Issue**: 
- Symbols may be delisted mid-period (no bars after delisting date)
- Symbols may have gaps in data due to halts or data issues
- OTC symbols require special subscription (broker partners only)

**Mitigation**:
- Check symbol status via Alpaca Assets API (`/v2/assets/{symbol}`)
- Verify `status: "active"` and `tradable: true`
- Handle `null` or missing bars gracefully
- Report delisted symbols separately

### 6. Symbol Name Changes

**Issue**: Companies may change ticker symbols (e.g., FB → META on 2022-06-09).

**Behavior**:
- Historical endpoints support `asof` parameter to map old symbols to new ones
- By default, querying new symbol returns data labeled with new symbol (including pre-rename data)
- `asof="-"` disables symbol mapping
- Symbol mapping available the day after rename (not same day)

**Recommendation**: Use `asof` parameter when querying symbols that may have been renamed.

### 7. Feed Selection and Subscription

**Issue**: 
- SIP feed requires subscription for recent data (<15 minutes old)
- Default feed is chosen based on subscription level
- IEX feed is free but covers only one exchange

**Recommendation**: 
- Use `feed=sip` for comprehensive data (if subscribed)
- Use `feed=iex` for free tier
- Document which feed is used in output

### 8. Limit Behavior

**Issue**: `limit` is global across all symbols, not per symbol.

**Example**: Requesting 1000 bars for 10 symbols does not guarantee 100 bars per symbol—one symbol might consume the entire limit.

**Mitigation**: 
- Use smaller `limit` values and paginate more frequently
- Or query symbols individually for predictable per-symbol limits

## Verification Checklist

Before implementation, verify the following:

- [ ] Confirm exact rate limit for your API key (check `X-RateLimit-Limit` header)
- [ ] Test pagination with multiple symbols to confirm symbol-first sorting behavior
- [ ] Verify timestamp format for daily bars (confirm `04:00:00Z` vs `00:00:00Z`)
- [ ] Test `adjustment="all"` vs `adjustment="raw"` to understand price differences
- [ ] Test `asof` parameter with a renamed symbol (e.g., META with `asof=2022-06-06`)
- [ ] Verify `feed` parameter behavior with and without subscription
- [ ] Test edge cases: empty date ranges, invalid symbols, delisted symbols
- [ ] Confirm `next_page_token` format and how it encodes symbol/timestamp state

## References

- [Alpaca Market Data API - Historical Bars](https://docs.alpaca.markets/reference/stockbars)
- [Getting Started with Market Data API](https://docs.alpaca.markets/docs/getting-started-with-alpaca-market-data)
- [Market Data FAQ](https://docs.alpaca.markets/docs/market-data-faq)
