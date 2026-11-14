package pvrlabs.stargazer;

import gg.jte.ContentType;
import gg.jte.TemplateEngine;
import gg.jte.output.StringOutput;

import java.util.Locale;
import java.util.Map;

public final class Views {
    private final TemplateEngine templates = TemplateEngine.createPrecompiled(ContentType.Html);

    public static String format(Integer value) {
        return value == null ? "—" : String.format(Locale.US, "%,d", value);
    }

    public String render(Map<String, Object> model) {
        var output = new StringOutput();
        templates.render(
                "index.jte",
                Map.of("cards", model.get("cards"), "chartJson", model.get("chartJson")),
                output);
        return output.toString();
    }
}
