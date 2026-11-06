package lab;
import java.util.*;
import java.sql.*;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Repository;
@Repository
public class QuoteRepository {
    private final NamedParameterJdbcTemplate db;
    public QuoteRepository(NamedParameterJdbcTemplate db) { this.db=db; }
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
    private List<Quotes.Quote> find(String symbol,int limit) { return db.query(SELECT, Map.of("symbol",symbol,"limit",limit), (rs, n) -> row(rs)); }
    public List<Quotes.Quote> history(String symbol,int limit) {
        var rows=new ArrayList<>(find(symbol,limit)); Collections.reverse(rows); return rows;
    }
    public void insert(Quotes.Batch b) {
        for(var symbol:Quotes.SYMBOLS) { db.update(INSERT, Map.of("sequence",b.sequence(),"cycle",b.cycle(),"sampleIndex",b.sampleIndex(),"marketTime",b.marketTime(),"symbol",symbol,"price",b.prices().get(symbol))); }
    }
    public Map<String,Object> state() { return db.queryForObject(STATE, Map.of(), (rs, n) -> stateRow(rs)); }
}
