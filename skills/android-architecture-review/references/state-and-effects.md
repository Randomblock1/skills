# State and effects

Verified: 2026-08-23.

The distinction that generates most of the correct answers in this layer, and the mechanisms that
implement it. Read this when state ownership, effect delivery, or UI state shape is in question.

## The test: does it survive a config change?

**Anything still true after rotation or process death is state. Anything the UI runs once and forgets
is an effect.**

That single question resolves most disputes. An error to display is *state* — it is still true after
rotation, so it belongs as a field in `UiState`. A navigation command is an *effect* — after rotation
you have either already navigated or you have not, and replaying it would navigate twice. A snackbar
sits closer to the line: "show this message" is an effect, but "this field is invalid" is state that
happens to be rendered transiently.

Getting this wrong produces two recognisable bugs. Errors modelled as effects vanish on rotation, so
the user rotates and their error message disappears. Navigation modelled as state re-navigates on
every recomposition or after process death, so the user comes back to the app and gets thrown
forward a screen.

## Delivering effects

Use a `Channel`, not a `SharedFlow`:

```kotlin
private val _effects = Channel<UiEffect>(Channel.BUFFERED)
val effects = _effects.receiveAsFlow()
```

The mechanism matters. A `MutableSharedFlow` with no replay **drops** an emission when there is no
active collector — and there is no active collector while the screen is backgrounded. A buffered
`Channel` holds it and delivers on resume. So the difference is not stylistic: with `SharedFlow`, an
effect emitted during a background operation that completes while the user is in another app is
silently lost.

Collect in a `LaunchedEffect` with `repeatOnLifecycle`:

```kotlin
val lifecycleOwner = LocalLifecycleOwner.current
LaunchedEffect(lifecycleOwner) {
    lifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
        viewModel.effects.collect { effect -> /* navigate, show snackbar */ }
    }
}
```

**Never `collectAsStateWithLifecycle` for effects.** It converts a stream into state with a retained
current value, which is exactly the property an effect must not have — the last effect becomes
sticky and refires on recomposition.

`receiveAsFlow` gives a single-consumer stream, which is what you want: an effect delivered to two
collectors navigates twice.

## Shaping UI state

Sort every field into one of four buckets. The bucket, not the field, dictates lifecycle and
persistence.

1. **Editable input** — what the user typed. Lives in the state holder, restored on config change,
   usually not persisted across screens.
2. **Derived** — computed from other fields. `canSubmit`, `hasErrors`, `formattedTotal`.
3. **Persisted snapshot** — must survive process death. Draft content, a wizard step.
4. **Transient UI-only** — `isSubmitting`, `showTooltip`. Reset on process death by design.

Each bucket has a specific failure mode when it is misclassified, which is what makes the taxonomy
worth applying rather than just knowing:

- Persisting `isSubmitting` (bucket 4 treated as 3) leaves the spinner spinning forever after process
  death, with no operation to complete it.
- Computing `canSubmit` outside the state class (bucket 2 treated as 1) lets it drift out of sync
  with the inputs it supposedly derives from.
- Persisting `cardNumber` across screens (bucket 1 treated as 3) leaks PII into saved state.

### Derived values are properties, not constructor parameters

```kotlin
data class FormState(
    val email: String = "",
    val password: String = "",
    val isSubmitting: Boolean = false,
) {
    val canSubmit: Boolean get() = email.isNotBlank() && password.length >= 8 && !isSubmitting
}
```

If `canSubmit` were a constructor parameter, any caller could `copy(canSubmit = true)` and produce a
state that claims to be submittable with an empty password. As a getter it cannot be inconsistent —
the invariant is structural rather than maintained by convention. This is the whole argument, and it
generalises: prefer making invalid states unrepresentable over documenting that they are invalid.

## Grouping callbacks

Individual lambdas are simpler and clearer below roughly four or five. Above that, or when the same
set threads through several composable layers, promote them:

```kotlin
@Stable
interface CheckoutActions {
    fun onEmailChange(value: String)
    fun onSubmit()
    fun onDismissError()
    fun onEditAddress()
    fun onSelectPayment(id: String)
}
```

The ViewModel implements it; the content composable depends on `CheckoutActions`, never on the
ViewModel. That keeps the composable previewable with `object : CheckoutActions { … }` and keeps the
parameter list stable as actions are added.

Do not abstract early. A two-lambda interface is ceremony, and `@Stable` on it is a promise you now
have to keep.

## Sealed hierarchies for screen state

A `sealed interface` per screen (`Loading` / `Content` / `Error`) is right when the states are
genuinely exclusive and carry different data. It is wrong when they overlap — a screen that shows
content *while* refreshing, or content *with* an inline error, needs a data class with flags, because
the sealed version forces you to either duplicate the content payload into the error case or lose it.

The tell that a sealed hierarchy was the wrong choice: an `Error` case that also carries the previous
content so the UI can keep rendering it.

## SavedStateHandle

Use it for what genuinely must survive process death — not for everything. Every key adds a
serialization contract you have to maintain, and the Bundle has a size limit that a large draft can
exceed. Navigation arguments arrive here already; re-storing them is duplication.

## Common defects, with the mechanism

| Pattern | Why it is wrong |
|---|---|
| `val uiState = MutableStateFlow(...)` exposed publicly | The UI can bypass every invariant the ViewModel maintains, and there is no single place to audit transitions. Expose `asStateFlow()`. |
| Many unrelated `StateFlow`s on one ViewModel | The UI recomposes on each independently and can render a combination that never validly co-occurred. Combine into one state object. |
| `LaunchedEffect(Unit)` for a once-per-screen action | Refires on configuration change. Key it, move it to `init`, or gate it in saved state. |
| `viewModelScope.launch` in a composable body | Runs on every recomposition. Effects belong in `LaunchedEffect` or in the ViewModel. |
| `collectAsState()` without lifecycle awareness | Collects while the screen is in the background, doing work and holding resources for a screen nobody is looking at. Use `collectAsStateWithLifecycle()`. |
| `GlobalScope.launch` | No cancellation, so the work outlives the screen and leaks. |
| A ViewModel holding a `Context`, `View`, or `NavController` | Leaks across configuration change, and makes the ViewModel untestable. Pass what is needed, or emit an effect. |
| `mutableStateOf` in a ViewModel exposed as `var` | Same as the first row, with a less obvious mutation site. |
