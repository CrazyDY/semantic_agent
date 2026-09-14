# Frontend reactivity fix

`useChatStream.ts` must keep the Proxy returned by Vue's reactive array after inserting an assistant message.
Do not mutate the raw object that was passed to `messages.value.push()`.

Root cause:
- `messages = ref([])` makes the array reactive.
- `push(rawObject)` inserts a proxied object into the reactive array.
- Keeping `activeAssistant = rawObject` and mutating `activeAssistant.turn.content` bypasses the Proxy.

The implementation now pushes first and then assigns:

```ts
messages.value.push({ id, role: 'assistant', turn })
activeAssistant = messages.value[messages.value.length - 1]
```
