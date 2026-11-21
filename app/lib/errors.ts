export type Result<T, E = Error> = [T, undefined] | [undefined, E]

export async function tryCatch<T, E = Error>(promise: Promise<T>): Promise<Result<T, E>> {
  try {
    return [await promise, undefined]
  } catch (err) {
    return [undefined, err as E]
  }
}


export const domainErrorTypes = ["username_taken"] as const
type DomainErrorType = typeof domainErrorTypes[number]

export class DomainError extends Error {
  constructor(public type: DomainErrorType, msg: string) {
    super(msg)
    this.type = type
  }
}
