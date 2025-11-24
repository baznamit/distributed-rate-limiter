# Race Condition Fix Documentation

## Problem: Race Condition in Rate Limiting

### The Issue
In the basic fixed window implementation (`fixed_window.py`), there's a potential race condition:

```python
# Step 1: Get current count
current_count = self.redis_client.get(key)  # Both requests might read "4"
current_count = int(current_count) if current_count else 0

# Step 2: Check limit
if current_count >= self.requests_limit:  # Both think they're under limit
    return False, {...}

# Step 3: Increment counter
pipe = self.redis_client.pipeline()
pipe.incr(key)  # Both increment, resulting in 6 requests allowed
```

### Race Condition Scenario
1. **Time T1**: Request A reads counter = 4
2. **Time T1**: Request B reads counter = 4 (same value!)
3. **Time T2**: Request A checks: 4 < 5 ✅ (allowed)
4. **Time T2**: Request B checks: 4 < 5 ✅ (allowed) 
5. **Time T3**: Request A increments counter: 4 → 5
6. **Time T3**: Request B increments counter: 5 → 6

**Result**: 6 requests allowed instead of 5! 🐛

## Solution: Atomic Operations with Lua Scripts

### How Lua Scripts Fix This
Redis Lua scripts execute **atomically** - no other command can run while the script is executing.

```lua
-- All these operations happen atomically:
local current_count = redis.call('GET', key)
if current_count >= limit then
    return {0, current_count, limit, window_end, retry_after}
end
local new_count = redis.call('INCR', key)
return {1, new_count, limit, window_end, 0}
```

### Atomic Execution Guarantee
1. **Time T1**: Request A starts Lua script
2. **Time T1**: Request B waits (cannot execute until A completes)
3. **Time T2**: Request A completes: counter = 5, allowed
4. **Time T3**: Request B starts Lua script
5. **Time T4**: Request B sees counter = 5, blocked ✅

**Result**: Exactly 5 requests allowed, as intended! ✅

## Implementation Comparison

| Feature | Basic Fixed Window | Atomic Fixed Window |
|---------|-------------------|-------------------|
| **Race Condition Safe** | ❌ No | ✅ Yes |
| **Atomic Operations** | ❌ Multiple Redis calls | ✅ Single Lua script |
| **Under High Load** | ❌ May exceed limit | ✅ Accurate limiting |
| **Performance** | ✅ Good | ✅ Better (fewer round trips) |
| **Complexity** | ✅ Simple | ⚠️ More complex |

## Testing Race Conditions

### Manual Test
```bash
# Terminal 1: Start atomic server
cd backend
python -m app.main_atomic

# Terminal 2: Run race condition test
python test_race_condition.py
```

### Expected Results
- **Without atomic operations**: Occasionally > 5 successful requests
- **With atomic operations**: Always ≤ 5 successful requests

### Load Test with Locust
```python
# In locust test (coming later):
# Send 100 concurrent requests
# Verify no more than 5 succeed per window
```

## Key Benefits of Atomic Implementation

1. **Correctness**: Never exceeds rate limits, even under extreme load
2. **Consistency**: Same behavior across multiple server instances
3. **Performance**: Fewer Redis round trips
4. **Reliability**: No timing-dependent bugs

## When to Use Each

### Use Basic Fixed Window When:
- Low to medium traffic
- Race conditions are unlikely
- Simplicity is preferred
- Occasional limit overage is acceptable

### Use Atomic Fixed Window When:
- High traffic with concurrent requests
- Strict rate limiting required
- Multiple server instances
- Production environments

## Next Steps
The atomic implementation will be used as the foundation for:
- FastAPI middleware integration
- Sliding window algorithm
- Advanced rate limiting features