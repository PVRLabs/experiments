package lab;
public final class RepositoryFailure extends RuntimeException {
    public enum Kind { CONFLICT, UNEXPECTED }
    private final Kind kind;
    public RepositoryFailure(Kind kind, Throwable cause) { super(kind.name(), cause); this.kind = kind; }
    public Kind kind() { return kind; }
}
