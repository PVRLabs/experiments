package pvrlabs.stargazer;

import static org.junit.jupiter.api.Assertions.*;

import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Proxy;
import java.util.concurrent.atomic.AtomicInteger;

class TransactionInitializationTest {
    @SuppressWarnings("unchecked")
    private static <T> T proxy(Class<T> type, java.lang.reflect.InvocationHandler handler) {
        return (T) Proxy.newProxyInstance(type.getClassLoader(), new Class<?>[] {type}, handler);
    }

    @Test
    void clearsContextWhenBeginFailsOnReusedThread() {
        var attempts = new AtomicInteger();
        var closed = new AtomicInteger();
        Transaction tx =
                proxy(Transaction.class, (p, m, a) -> m.getName().equals("isActive") ? true : null);
        Session session =
                proxy(
                        Session.class,
                        (p, m, a) -> {
                            if (m.getName().equals("beginTransaction")) {
                                if (attempts.getAndIncrement() == 0) {
                                    throw new IllegalStateException("injected begin failure");
                                }
                                return tx;
                            }
                            if (m.getName().equals("close")) {
                                closed.incrementAndGet();
                            }
                            return null;
                        });
        SessionFactory factory =
                proxy(
                        SessionFactory.class,
                        (p, m, a) -> m.getName().equals("openSession") ? session : null);
        try (var store = new HibernateStore(factory)) {
            assertEquals(
                    "injected begin failure",
                    assertThrows(IllegalStateException.class, () -> store.transaction(() -> 1))
                            .getMessage());
            assertEquals(42, store.transaction(() -> 42));
            assertEquals(2, closed.get());
        }
    }
}
