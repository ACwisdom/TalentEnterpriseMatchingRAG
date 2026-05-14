package com.talent.recruitment.domain;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;
import java.util.EnumSet;
import java.util.Set;
import lombok.Getter;
import lombok.RequiredArgsConstructor;

@Getter
@RequiredArgsConstructor
public enum RecommendationStatus {
    已推荐("已推荐"),
    已读("已读"),
    有意向("有意向"),
    面试("面试"),
    offer("offer"),
    入职("入职"),
    不合适("不合适");

    private final String value;

    @JsonValue
    public String getValue() {
        return value;
    }

    @JsonCreator
    public static RecommendationStatus fromValue(String raw) {
        if (raw == null) {
            return null;
        }
        for (RecommendationStatus s : values()) {
            if (s.value.equals(raw)) {
                return s;
            }
        }
        throw new IllegalArgumentException("Unknown status: " + raw);
    }

    public static boolean isTerminal(RecommendationStatus s) {
        return s == 入职 || s == 不合适;
    }

    public static Set<RecommendationStatus> allowedNext(RecommendationStatus current) {
        return switch (current) {
            case 已推荐 -> EnumSet.of(已读, 不合适);
            case 已读 -> EnumSet.of(有意向, 不合适);
            case 有意向 -> EnumSet.of(面试, 不合适);
            case 面试 -> EnumSet.of(offer, 不合适);
            case offer -> EnumSet.of(入职, 不合适);
            case 入职, 不合适 -> EnumSet.noneOf(RecommendationStatus.class);
        };
    }
}
