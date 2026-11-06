package lab;
import java.util.*;
import java.sql.*;
import pvrlabs.coilbase.RepositoryContext;

public class QuoteRepository {
    private final RepositoryContext db;
    public QuoteRepository(RepositoryContext db) { this.db=db; }
    private static final String SELECT="SELECT batch_seq,cycle,sample_index,market_time,symbol,price FROM quotes WHERE symbol=:symbol ORDER BY id DESC LIMIT :limit";
    private static final String INSERT="INSERT INTO quotes(batch_seq,cycle,sample_index,market_time,symbol,price) VALUES(:sequence,:cycle,:sampleIndex,:marketTime,:symbol,:price)";
    private static final String STATE="SELECT COUNT(*) AS rows,MAX(batch_seq) AS maxSequence,SUM(price) AS priceSum FROM quotes";
    private static Quotes.Quote row(ResultSet rs) throws SQLException {
        return new Quotes.Quote(rs.getInt(1),rs.getInt(2),rs.getInt(3),rs.getString(4),rs.getString(5),rs.getBigDecimal(6));
    }
    private static Map<String,Object> stateRow(ResultSet rs) throws SQLException {
        return Map.of("rows",rs.getInt(1),"maxSequence",rs.getInt(2),"priceSum",rs.getBigDecimal(3));
    }
    public List<Quotes.Quote> latest() {
        var rows=new ArrayList<Quotes.Quote>();
        for(var symbol:Quotes.SYMBOLS) rows.addAll(find(symbol,1));
        return rows;
    }
    private List<Quotes.Quote> find(String symbol,int limit) { return db.query(SELECT, q -> q.bind("symbol",symbol).bind("limit",limit).map((rs, ctx) -> row(rs)).list()); }
    public List<Quotes.Quote> history(String symbol,int limit) {
        var rows=new ArrayList<>(find(symbol,limit)); Collections.reverse(rows); return rows;
    }
    public void insert(Quotes.Batch b) {
        for(var symbol:Quotes.SYMBOLS) { db.update(INSERT, q -> q.bind("sequence",b.sequence()).bind("cycle",b.cycle()).bind("sampleIndex",b.sampleIndex()).bind("marketTime",b.marketTime()).bind("symbol",symbol).bind("price",b.prices().get(symbol)).execute()); }
    }
    public Map<String,Object> state() { return db.query(STATE, q -> q.map((rs, ctx) -> stateRow(rs)).one()); }
}
