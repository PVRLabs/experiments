import lab.Quotes;
import java.math.BigDecimal;
import java.util.Map;
public class AtomicCheck {
 public static void main(String[] args) throws Exception {
  System.setProperty("run.dir",args[0]);
  try(var ds=Quotes.dataSource()) {
   var q=new Quotes(ds);
   if(((Number)q.state().get("rows")).intValue()!=1170)throw new AssertionError();
   try(var c=ds.getConnection();var s=c.createStatement()) {s.executeUpdate("INSERT INTO quotes(batch_seq,cycle,sample_index,market_time,symbol,price) VALUES(999,1,0,'09:30','GOOG',1)");}
   var before=q.state();
   try {q.insert(new Quotes.Batch(999,1,0,"09:30",Map.of("AAPL",BigDecimal.ONE,"GOOG",BigDecimal.ONE,"NVDA",BigDecimal.ONE)));throw new AssertionError("Expected duplicate failure");}catch(java.sql.SQLException expected){}
   if(!q.state().equals(before))throw new AssertionError("Partial write persisted");
   System.out.println("PASS: partial-batch duplicate rolls back earlier successful insert");
  }
 }
}
