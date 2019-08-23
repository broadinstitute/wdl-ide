package org.broadinstitute.wdl.devtools;

import com.intellij.openapi.project.Project;
import com.intellij.openapi.startup.StartupActivity;
import com.intellij.profile.codeInspection.InspectionProjectProfileManager;
import org.jetbrains.annotations.NotNull;

import java.util.Collections;

public final class PluginStartupActivity implements StartupActivity {
    public void runActivity(@NotNull final Project project) {
        InspectionProjectProfileManager.getInstance(project)
                .getCurrentProfile().disableToolByDefault(
                    Collections.singletonList("SpellCheckingInspection"), project
        );
    }
}
