class CodeReviewError(Exception): pass
class EmptyCodeError(CodeReviewError): pass
class CodeTooLongError(CodeReviewError): pass
class LLMCallError(CodeReviewError): pass
class ReportParseError(CodeReviewError): pass
class MaxIterationError(CodeReviewError): pass