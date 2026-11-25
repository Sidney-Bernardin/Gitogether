export type Result<T, E = Error> = [T, undefined] | [undefined, E]

export function trySync<T, E = Error>(fn: () => T): Result<T, E> {
  try {
    return [fn(), undefined]
  } catch (err) {
    return [undefined, err as E]
  }
}

export async function tryAsync<T, E = Error>(promise: Promise<T>): Promise<Result<T, E>> {
  try {
    return [await promise, undefined]
  } catch (err) {
    return [undefined, err as E]
  }
}
