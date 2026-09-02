# Data layer and error propagation

Verified: 2026-08-23. Room facts verified against Room 3.0.1 release notes.

Where errors get mapped, and why the layer matters more than the mechanism.

## The error ladder

Four rungs. The value of naming them is that "where do I catch this" becomes a structural question
with one answer, rather than a judgment call made differently in every file.

1. **Data sources throw.** A Retrofit service, a DAO, a `DataStore` read — these throw platform
   exceptions: `IOException`, `HttpException`, `SQLiteException`, `SerializationException`. Do not
   wrap them here. The data source's job is access, not interpretation.

2. **The repository is the error boundary.** This is the only layer that catches platform exception
   types, because it is the only layer that knows which platform it is talking to. It maps them to a
   domain error:

   ```kotlin
   sealed interface DataError {
       data object Network : DataError
       data object Unauthorized : DataError
       data class Http(val code: Int) : DataError
       data object Storage : DataError
       data class Unknown(val cause: Throwable) : DataError
   }
   ```

3. **Use cases are the `Result` boundary** — when a domain layer exists. They compose repository
   calls and return `Result<T>` (or an equivalent `Either`). **Use cases never catch platform
   exception types.** If a use case has a `catch (e: IOException)`, the repository above it failed to
   do its job, and that is the real finding.

   Without a domain layer, the repository returns `Result<T>` directly. Both shapes are legitimate;
   what is not legitimate is having both in the same codebase for the same kind of call.

4. **ViewModels map `Result` to explicit state.** `Result.failure(DataError.Network)` becomes
   `uiState.copy(error = UiText.NoConnection)`. The UI layer never sees a `Throwable`, and never
   decides what an `HttpException` means.

The failure this prevents: `try/catch` sprinkled at every layer, each one catching a bit and
rethrowing something slightly different, so nobody can say what a given call can fail with.

## Findings to look for

| Pattern | The finding |
|---|---|
| `catch (e: IOException)` in a use case or ViewModel | The repository is not acting as the boundary. Move the mapping down. |
| `catch (e: Exception)` anywhere | Swallows `CancellationException`, which breaks coroutine cancellation. Rethrow it, or catch specific types. |
| `Result<Result<T>>`, or a `Result` unwrapped and rewrapped at each layer | Two boundaries doing the same job. Pick one rung. |
| Two error sealed hierarchies for the same failures | Usually two features that grew independently. Consolidate, or document why they differ. |
| A `Throwable` in `UiState` | The UI now decides what an exception means, in a layer with no knowledge to decide it. Map to a UI-facing type. |
| `runCatching` around a whole repository method | Catches `CancellationException` too, and loses the specific mapping. |
| Error strings built in the data layer | Localisation and context belong to the UI layer. Pass a type, resolve the string at render. |

## Cancellation

`CancellationException` is control flow, not an error. Any `catch (e: Exception)` or bare
`runCatching` that does not rethrow it turns a cancelled coroutine into a spurious error state — and
the symptom is a screen that shows an error when the user navigates away quickly.

```kotlin
try { … } catch (e: CancellationException) { throw e } catch (e: IOException) { … }
```

`kotlin.Result` and `runCatching` both capture `CancellationException`. If the project uses them
broadly, that is worth flagging once rather than at every site.

## Flow exposure

Repositories should expose cold `Flow`s and let the caller decide the sharing policy. A repository
that internally calls `stateIn(GlobalScope, …)` has made a lifetime decision on behalf of every
consumer, and made itself untestable.

`.catch { }` on a `Flow` in the repository is the boundary in stream form — map there, and emit a
`Result` or a domain error rather than letting the exception cancel the collector.

## Room 3

Room 3.0.1 is stable (July 2026) and the artifacts moved: **`androidx.room3:room3-*`**. Four changes
matter for review, and models routinely emit the pre-3.0 forms:

- **`@TypeConverter` was renamed `@ColumnTypeConverter`** (in 3.0.0-rc01).
- **`@DaoReturnTypeConverter(s)` is new**, replacing the built-in Paging, RxJava, Guava, and LiveData
  integrations. Code relying on those integrations implicitly needs the annotation now.
- **KSP only.** Room 3 has no Java codegen path, so KAPT is not merely discouraged — it is
  impossible. A project on KAPT for Room must move to KSP as part of upgrading.
- **A `SQLiteDriver` is now required** to build a `RoomDatabase`. Omitting it is a build-time failure,
  not a runtime default.

Ordinary Room review still applies: migrations tested rather than `fallbackToDestructiveMigration()`
in release, indices on columns you query, `@Transaction` on multi-statement DAO methods, and no
`allowMainThreadQueries()`.

## DataStore and preferences

Proto DataStore for typed data, Preferences DataStore for key-value. Both are `Flow`-based and
asynchronous, which is the point — a `SharedPreferences` read on the main thread is a real jank
source, and the synchronous API makes it easy to do accidentally.

Do not put anything sensitive in either without encryption, and do not use DataStore as a database:
the whole file is read and rewritten, so a growing list belongs in Room.

## Repository shape

- One repository per data concept, not per screen. A `ProfileScreenRepository` is a naming smell that
  usually means the data layer is tracking the UI.
- The repository owns the cache policy — single source of truth, usually the local database, with the
  network writing into it and the UI reading from it. A repository that returns network data directly
  *and* writes it to the database creates two sources of truth that drift.
- Interface plus implementation is worth it when there are multiple implementations or when the
  boundary is a module API. For a single implementation inside one module it is often ceremony —
  though if the project already does it everywhere, follow the project.
- Inject dispatchers rather than hardcoding `Dispatchers.IO`, so tests can substitute. Suspend
  functions should be main-safe: the caller should not need to know which dispatcher to use.
