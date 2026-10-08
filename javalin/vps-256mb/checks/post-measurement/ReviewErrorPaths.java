import lab.Quotes;
import lab.SqlErrors;
import java.sql.SQLException;
public final class ReviewErrorPaths {
    public static void main(String[] args) throws Exception {
        System.setProperty("run.dir", args[0]);
        try (var ds = Quotes.dataSource()) {
            var quotes = new Quotes(ds);
            for (String symbol : new String[] {null, "INVALID"}) {
                try { quotes.history(symbol, 60); throw new AssertionError("Invalid symbol accepted"); }
                catch (IllegalArgumentException expected) {}
            }
            if (quotes.history("AAPL",60).size()!=60) throw new AssertionError("Valid history changed");
        }
        if (SqlErrors.status(new SQLException("constraint","23505"))!=409) throw new AssertionError();
        if (SqlErrors.status(new SQLException("unexpected","08001"))!=500) throw new AssertionError();
        var missing = new SQLException("missing state");
        if (SqlErrors.status(missing)!=500 || !SqlErrors.code(missing).equals("unknown")) throw new AssertionError();
        System.out.println("PASS: missing/invalid history symbols and null/constraint/unexpected SQL states");
    }
}
