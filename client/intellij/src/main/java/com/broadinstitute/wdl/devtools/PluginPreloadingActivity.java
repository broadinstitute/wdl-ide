package com.broadinstitute.wdl.devtools;

import com.intellij.ide.plugins.PluginManager;
import com.intellij.openapi.application.PreloadingActivity;
import com.intellij.openapi.extensions.PluginId;
import com.intellij.openapi.progress.ProgressIndicator;

import org.jetbrains.annotations.NotNull;
import org.jetbrains.plugins.textmate.TextMateService;
import org.jetbrains.plugins.textmate.configuration.BundleConfigBean;
import org.jetbrains.plugins.textmate.configuration.TextMateSettings;

import org.wso2.lsp4intellij.IntellijLanguageClient;
import org.wso2.lsp4intellij.client.languageserver.serverdefinition.ExeLanguageServerDefinition;

import java.io.File;
import java.util.Collections;

public final class PluginPreloadingActivity extends PreloadingActivity {

    private static final String PLUGIN_ID = "org.broadinstitute.wdl.devtools";

    private static final String BUNDLE = "WDL";

    private static final String EXTENSION = "wdl";
    private static final String PYTHON_PATH = "python3";
    private static final String SERVER_MODULE = "wdl_lsp";

    @Override
    public void preload(@NotNull ProgressIndicator indicator) {
        setupSyntaxHighlighting();

        setupLanguageServer();
    }

    private void setupSyntaxHighlighting() {
        TextMateSettings.TextMateSettingsState state = TextMateSettings.getInstance().getState();
        if (state == null) {
            state = new TextMateSettings.TextMateSettingsState();
        }

        final File pluginDir = PluginManager.getPlugin(PluginId.getId(PLUGIN_ID)).getPath();
        final String bundlePath = new File(pluginDir, "WDL.tmbundle").getAbsolutePath();
        final BundleConfigBean bundle = new BundleConfigBean(BUNDLE, bundlePath, true);

        state.setBundles(Collections.singleton(bundle));
        TextMateSettings.getInstance().loadState(state);
        TextMateService.getInstance().registerEnabledBundles(false);
    }

    private void setupLanguageServer() {
        IntellijLanguageClient.addServerDefinition(
                new ExeLanguageServerDefinition(EXTENSION, PYTHON_PATH, new String[]{"-m", SERVER_MODULE})
        );
    }
}
